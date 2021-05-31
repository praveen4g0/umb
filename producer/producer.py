import argparse
import threading
import collections
from proton.handlers import MessagingHandler
from proton.reactor import Container, Selector
from proton import SSLDomain, Message
import json
import logging
from flask import Flask, request, abort, jsonify
import os
import socket
from os.path import dirname, join
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
        self._logger.info('{0}: message accepted! and now closing connection!'.format(threading.currentThread().getName()))
        event.connection.close()

    def on_rejected(self, event):
         self._logger.info("{0}: Broker {1} Rejected message: {2}, Remote disposition: {3}".format(threading.currentThread().getName(),self.urls,event.delivery.tag,event.delivery.remote.condition))

    # receives socket or authentication failures
    def on_transport_error(self, event):
        self._logger.info("{0}: Transport failure for amqp broker: {1} Error: {2}".format(threading.currentThread().getName(),self.urls,event.transport.condition))
        MessagingHandler.on_transport_error(self, event)           

def setup_logging(verbose):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.environ.get('CONFIG_FILE',None))
    parser.add_argument("-v", "--verbose", action='store_true')
    return parser.parse_args()

class UmbProducerService(object):
    def __init__(self, topic,message,configmap):
        self.up = UMBMessageProducer(topic,message,configmap)
        self.container = Container(self.up)

    def start(self):
        try:
            self.container.run()
        except KeyboardInterrupt: pass
    def stop(self):
        try:
           self.container.stop()
        except KeyboardInterrupt: pass

def producerServiceStart(topic,message):
    UmbProducerService(topic,message,ConfigurationManager(cfg_path=args.config)).start()

def producerServiceStop(topic,message):
    UmbProducerService(topic,message,ConfigurationManager(cfg_path=args.config)).stop()    

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
            producerServiceStop(data['topic'],data['message'])
            return jsonify({"Message": "message sent successfully! to {0}".format(data['topic'])}),200   
        elif isinstance(data['message'],dict): 
            producerServiceStart(data['topic'],json.dumps(data['message']))
            producerServiceStop(data['topic'],data['message'])
            return jsonify({"Message": "message sent successfully! to {0}".format(data['topic'])}),200
        else:
            return jsonify({"Error": "we don't support messages of type {}".format(type(data['message']))}),400    
    else:
      abort(400)

if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    app.run(host='0.0.0.0', port=8080, debug=False)