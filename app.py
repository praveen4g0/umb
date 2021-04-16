import argparse
import threading
from proton.handlers import MessagingHandler
from proton.reactor import Container, Selector
from proton import SSLDomain
import json
from jsonpath_rw import jsonpath, parse
import logging
from flask import Flask
import os
import socket

hostname = socket.gethostname()

app = Flask(__name__)

from os.path import dirname, join
import logging
import yaml

DEFAULT_CONFIG_PATH = join(dirname(__file__),
                           "config", "config.yaml")


class ConfigurationManager(object):

    def __init__(self, cfg_path=None):
        cfg_path = cfg_path if cfg_path else DEFAULT_CONFIG_PATH
        self._logger = logging.getLogger(__name__)
        with open(cfg_path, 'r') as yaml_data:
            self._config = yaml.load(yaml_data,Loader=yaml.FullLoader)

    def _get_config(self):
        return self._config

    def _get_kafka_config(self):
        return self._get_config().get('kafka', dict())

    def _get_umb_config(self):
        key = 'umb' if 'umb' in self._config else 'amq'
        return self._get_config().get(key, dict())

    @property
    def producer_enabled(self):
        return self._get_kafka_config().get('enabled', True)

    def get_kafka_topic(self):
        return self._get_kafka_config().get('topic')

    def get_eventlistener(self):
        return self._get_umb_config().get('el_url')

    def get_selector(self):
        return self._get_umb_config().get('selector')    

    def get_producert_testComplete_kafka_topic(self):
        return self._get_umb_config().get('prodcuer_test_complete_topic')

    def get_producert_testError_kafka_topic(self):
        return self._get_umb_config().get('producer_test_error_topic')    

    def get_kafka_broker(self):
        return self._get_kafka_config().get('url')

    def get_umb_topic(self):
        return self._get_umb_config().get('topic')

    def get_umb_consumer(self):
        return self._get_umb_config().get('consumer')

    def get_umb_cert_path(self):
        return self._get_umb_config().get('certificate')

    def get_umb_private_key_path(self):
        return self._get_umb_config().get('private_key')

    def get_umb_brokers(self):
        urls = self._get_umb_config().get('url')
        return [urls] if isinstance(urls, str) else urls
   
class consumerProcessEvent(object):
    def __init__(self,configmap):
      self._logger = logging.getLogger(__name__)
      self.el = configmap.get_eventlistener()
      self.selector= configmap.get_selector()
    
    def normalize(self,event):
        body=event.message.body
        try:
            try:
                if isinstance(body,bytes):
                   body = event.message.body.decode("utf-8")
            except UnicodeEncodeError:
                self._logger.error("Could not decode message body")
                raise
            self._logger.debug("Parsing Event: {0}".format(body))
            body = json.loads(body)
        except ValueError:
            self._logger.info("Cannot parse message: not valid JSON.")
            self._logger.info("Assuming message is a simple string.")
            try:
                body = str(body)
            except ValueError:
                raise
        return body

    def process_event(self, event):
        normalized = self.normalize(event)
        if isinstance(normalized, dict):
             selector,expected_val= str(self.selector).split(',')[0],str(self.selector).split(',')[1]
             jsonpath_expr = parse(selector)
             try:
                match = jsonpath_expr.find(normalized)
                if str(match[0].value).find(expected_val) != -1:
                    self._logger.info("Recived Message to process... ")
                    self._logger.info(normalized)
                    self._logger.info("We are sending processed messages to eventlisteners {0} ".format(self.el))
                else:
                    self._logger.info("message didn't pass filter check.")
                    self._logger.info(normalized)
             except IndexError:
                self._logger.debug(normalized)
                raise       
             except Exception as e:
                self._logger.debug(normalized) 
                raise
        else:   
           self._logger.debug("We aren't supporting text based messages {0} yet!".format(normalized))

class UmbReader(MessagingHandler):
    def __init__(self, configmap):
        super(UmbReader, self).__init__()
        self._logger = logging.getLogger(__name__)
        self.consumerProcessEvent = consumerProcessEvent(configmap)
        self.umb_topic = configmap.get_umb_topic()
        self.consumer = configmap.get_umb_consumer()
        self.cert = configmap.get_umb_cert_path()
        self.key = configmap.get_umb_private_key_path()
        self.urls = configmap.get_umb_brokers()
    def get_consumer_queue_str(self):
        seperator = '' if self.consumer.endswith('.') else '.'
        return '{}{}{}'.format(self.consumer, seperator, self.umb_topic)

    def get_selector(self):
        return None

    def on_start(self, event):
        domain = SSLDomain(SSLDomain.MODE_CLIENT)
        domain.set_credentials(self.cert, self.key, None)
        conn = event.container.connect(urls=self.urls, ssl_domain=domain)
        source = self.get_consumer_queue_str()
        event.container.create_receiver(conn, source=source,
                                        options=self.get_selector())
        self._logger.info("Subscribed to topic {0}".format(source))
    

    def on_message(self, event):
        try:
            self._logger.info(type(event.message.body))
            self.consumerProcessEvent.process_event(event)
        except Exception:
            self._logger.error("Could Not Process Event, Will Ignore. Error Info:",
                               exc_info=True)
  

def setup_logging(verbose):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=None)
    parser.add_argument("-v", "--verbose", action='store_true')
    return parser.parse_args()


class UmbConsumerService(object):
    
    def __init__(self, configmap):
        self.ur = UmbReader(configmap)
        self.container = Container(self.ur)

    def start(self):
        try:
            self.container.run()
        except KeyboardInterrupt: pass


def Consumerstart():
    UmbConsumerService(ConfigurationManager(cfg_path=args.config)).start()

@app.route("/")
def hello():
    return json.dumps({"Message": "Hello World!"})

@app.route("/consume")
def startConsumer():
    t = threading.Thread(target=Consumerstart)
    t.start()
    return json.dumps({"Message": "Consumer Registered successfully!"})

if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    app.run(host='0.0.0.0', port=8080, debug=True)