import argparse
import threading
import collections
import concurrent.futures.thread
from concurrent.futures import ThreadPoolExecutor,as_completed
from proton.handlers import MessagingHandler
from proton.reactor import Container, Selector
from proton import SSLDomain, Message
import json
from jsonpath_rw import jsonpath, parse
import logging
from flask import Flask, request, abort, jsonify
import os
import socket
from os.path import dirname, join
import requests
from requests import ReadTimeout, ConnectTimeout, HTTPError, Timeout, ConnectionError
import yaml

hostname = socket.gethostname()

app = Flask(__name__)

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

    def _get_umb_config(self):
        key = 'umb' if 'umb' in self._config else 'amq'
        return self._get_config().get(key, dict())    
    
    def get_subscribiers_config_list(self):
        key = 'subscriber'
        Subscriber = collections.namedtuple("Subscriber", ["topic", "selector", "sink_url"])
        return [Subscriber(**x) for x in self._get_config().get(key, list())]

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
    def __init__(self,selector,sink_url):
      self._logger = logging.getLogger(__name__)
      self.el = sink_url
      self.selector= selector
    
    def normalize(self,event):
        body=event.message.body
        try:
            try:
                if isinstance(body,bytes):
                   body = event.message.body.decode("utf-8")
            except UnicodeEncodeError:
                self._logger.error("{0}: Could not decode message body".format(threading.currentThread().getName()))
                raise
            self._logger.debug("{0}: Parsing Event: {1}".format(threading.currentThread().getName(),body))
            body = json.loads(body)
        except ValueError:
            self._logger.info("{0}: Cannot parse message: not valid JSON.".format(threading.currentThread().getName()))
            self._logger.info("{0}: Assuming message is a simple string.".format(threading.currentThread().getName()))
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
                    self._logger.info("{0}: Recived Message to process... ".format(threading.currentThread().getName()))
                    self._logger.info(type(normalized))
                    self._logger.info("{0}: We are sending processed messages to eventlisteners {1} ".format(threading.currentThread().getName(),self.el))
                    headers = { 'content-type': 'application/json' }
                    try:
                        res = requests.post(self.el,data=json.dumps(normalized),headers=headers)
                        self._logger.info(res.content)   
                    except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError) as e:
                        self._logger.info("{0}: Ahh, something went wrong! Check sink-url {1} health status".format(threading.currentThread().getName(),self.el))
                        self._logger.error(str(e),exc_info=True)
                else:
                    self._logger.info("{0}: message didn't pass filter check.".format(threading.currentThread().getName()))
                    self._logger.info(normalized)
             except IndexError:
                self._logger.debug(normalized)
                raise       
             except Exception as e:
                self._logger.debug(normalized) 
                raise
        else:   
           self._logger.debug("{0}: We aren't supporting text based messages {1} yet!".format(threading.currentThread().getName(),normalized))

"""
Proton event Handler class
Establishes an amqp connection and creates an amqp sender link to transmit messages
"""

class UMBMessageProducer(MessagingHandler):
    def __init__(self, address, message,configmap):
        super(UMBMessageProducer, self).__init__()
        self._logger = logging.getLogger(__name__)
        self.cert = configmap.get_umb_cert_path()
        self.key = configmap.get_umb_private_key_path()
        self.urls = configmap.get_umb_brokers()
         # the prefix amqp address for a solace topic
        self.topic_address = address
        self.message = message

    def on_start(self, event):
        # select authentication from SASL PLAIN or SASL ANONYMOUS
        domain = SSLDomain(SSLDomain.MODE_CLIENT)
        domain.set_credentials(self.cert, self.key, None)
        conn = event.container.connect(urls=self.urls, ssl_domain=domain)
        if conn:
            # creates sender link to transfer message to the broker
            event.container.create_sender(conn, target=self.topic_address)
            self._logger.info("{0}: created a link to senders to topic {1}".format(threading.currentThread().getName(),self.topic_address))
   
    def on_sendable(self, event):
        if isinstance(self.message,str):
            event.sender.send(Message(body=self.message,durable=True))
            event.sender.close()
        else:
            self._logger.error("{0}: Could Not Process message of type: {1}, expected type: (str) ".format(threading.currentThread().getName(),type(self.message)),
                               exc_info=True)
    
    def on_accepted(self, event):
        self._logger.info('{0}: message accepted! now closing connection'.format(threading.currentThread().getName()))
        event.connection.close()

    def on_rejected(self, event):
         self._logger.info("{0}: Broker {1} Rejected message: {2}, Remote disposition: {3}".format(threading.currentThread().getName(),self.urls,event.delivery.tag,event.delivery.remote.condition))

    # receives socket or authentication failures
    def on_transport_error(self, event):
        self._logger.info("{0}: Transport failure for amqp broker: {1} Error: {2}".format(threading.currentThread().getName(),self.urls,event.transport.condition))
        MessagingHandler.on_transport_error(self, event)           

class UmbReader(MessagingHandler):
    def __init__(self, topic,selector,sink_url,configmap):
        super(UmbReader, self).__init__()
        self._logger = logging.getLogger(__name__)
        self.consumerProcessEvent = consumerProcessEvent(selector,sink_url)
        self.topic=topic
        self.consumer = configmap.get_umb_consumer()
        self.cert = configmap.get_umb_cert_path()
        self.key = configmap.get_umb_private_key_path()
        self.urls = configmap.get_umb_brokers()
    def get_consumer_queue_str(self):
        seperator = '' if self.consumer.endswith('.') else '.'
        return '{}{}{}'.format(self.consumer, seperator, self.topic)

    def get_selector(self):
        return None

    def on_start(self, event):
        domain = SSLDomain(SSLDomain.MODE_CLIENT)
        domain.set_credentials(self.cert, self.key, None)
        conn = event.container.connect(urls=self.urls, ssl_domain=domain)
        source = self.get_consumer_queue_str()
        if conn:
            event.container.create_receiver(conn, source=source,
                                            options=self.get_selector())
            self._logger.info("{0} Subscribed to topic {1}".format(threading.currentThread().getName(),source))
        

    def on_message(self, event):
        try:
            self._logger.info(type(event.message.body))
            self.consumerProcessEvent.process_event(event)
        except Exception:
            self._logger.error("{0}: Could Not Process Event, Will Ignore. Error Info:".format(threading.currentThread().getName()),
                               exc_info=True)
  

def setup_logging(verbose):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.environ.get('CONFIG_FILE',None))
    parser.add_argument("-v", "--verbose", action='store_true')
    return parser.parse_args()


class UmbConsumerService(object):
    
    def __init__(self, topic,selector,sink_url,configmap):
        self.ur = UmbReader(topic,selector,sink_url,configmap)
        self.container = Container(self.ur)

    def start(self):
        try:
            self.container.run()
        except KeyboardInterrupt: pass

class UmbProducerService(object):
    def __init__(self, topic,message,configmap):
        self.up = UMBMessageProducer(topic,message,configmap)
        self.container = Container(self.up)

    def start(self):
        try:
            self.container.run()
        except KeyboardInterrupt: pass

def consumerStart(topic,selector,sink_url,configmap):
    UmbConsumerService(topic,selector,sink_url,configmap).start()

def producerServiceStart(topic,message):
    UmbProducerService(topic,message,ConfigurationManager(cfg_path=args.config)).start()

@app.route("/")
def hello():
    return jsonify({"Message": "Hello World!"}),200

@app.route('/produce', methods=['POST'])                                                                                                    
def prodcueUMBMessage(): 
    if not request.json:
        abort(400)
    if request.method == 'POST':                                                                                                                                 
        data = request.get_json()
        if isinstance(data['message'],str):
            producerServiceStart(data['topic'],data['message'])
            return jsonify({"Message": "message sent successfully! to {0}".format(data['topic'])}),200   
        elif isinstance(data['message'],dict): 
            producerServiceStart(data['topic'],json.dumps(data['message']))
            return jsonify({"Message": "message sent successfully! to {0}".format(data['topic'])}),200
        else:
            return jsonify({"Error": "we don't support messages of type {}".format(type(data['message']))}),400    
    else:
      abort(400)

if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    executor=ThreadPoolExecutor(max_workers=3)
    config=ConfigurationManager(cfg_path=args.config)
    futures=[executor.submit(consumerStart,subscriber.topic, subscriber.selector, subscriber.sink_url,config) for subscriber  in config.get_subscribiers_config_list()]
    print("Consumer Registered successfully!")
    app.run(host='0.0.0.0', port=8080, debug=True)
    try:
        for future in as_completed(futures):
            future.result()
    except KeyboardInterrupt:
        executor._threads.clear()
        concurrent.futures.thread._threads_queues.clear()
        executor.shutdown(True)