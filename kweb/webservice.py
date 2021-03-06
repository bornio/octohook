from __future__ import print_function
import bottle
import yaml
from .gitcommander import CommandParser, GitEventWatcher
import logging

class SSLWSGIRefServer(bottle.ServerAdapter):
    def run(self, handler):
        self.certfile = 'keys/server.pem'

        from wsgiref.simple_server import make_server, WSGIRequestHandler
        import ssl
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw): pass
            self.options['handler_class'] = QuietHandler
        srv = make_server(self.host, self.port, handler, **self.options)
        try:
            with open(self.certfile):
                pass
            srv.socket = ssl.wrap_socket(
                srv.socket,
                certfile=self.certfile
                )
            srv.serve_forever()
        except IOError as e:
            logging.error("Unable to open Certificate file at location {} {}".
                  format(self.certfile, e))
            raise


class WService(object):
    def __init__(self, queue, config):
        self.queue = queue
        self.config = config

    def exf_server(self):
      if bottle.request.method == 'POST':

         # Enable GitHub Hooking
         if bottle.request.get_header('X-GitHub-Event') == 'ping':
            return

         # No need to load JSON from body string, it;s pre-parsed by bottle...
         call = bottle.request.json
         if 'action' in call:
            logging.debug("Incoming request: {}".format(call['action']))
            if call['action'] == 'labeled':
               # process newly created issue
               if 'issue' in call:
                  if 'body' in call['issue'] and \
                        'labels' in call['issue'] and \
                        'name' in call['issue']['labels'][0]:
                        try:
                           # which agent is calling us
                           agentid = call['issue']['labels'][0]['name']
                           issue = call['issue']['number']

                           # what is this agent's instructions
                           body = yaml.load(call['issue']['body'])
                           logging.info("Instructions from Agent ({}) Issue ({}) "
                                                .format(agentid, issue))
                           c = CommandParser(self.config, agentid, issue)
                           c.parse(body)
                        except yaml.scanner.ScannerError as yse:
                           logging.error("This body of this issue cannot be parsed: {}".
                                 format(yse))
                           logging.debug(call['issue']['body'])
                  else:
                     logging.error("This issue does not have a body or named labels")
               else:
                  logging.error("This call is not a valid labeled issue")
            else:
               logging.debug("This call is not a labeled issue")
         else:
            logging.error("This call has no action")

    def exf_client(self):
      if bottle.request.method == 'POST':

         # Enable GitHub Web Hooking registration
         if bottle.request.get_header('X-GitHub-Event') == 'ping':
            return

         call=bottle.request.json
         if call is not None:
            logging.debug("X-GitHub-Event: {}".format(
                    bottle.request.get_header('X-GitHub-Event')))
            logging.debug("Agent: {}".format(
                self.config.client()['general']['boot']['agentid']))
            # Watch Events
            gew = GitEventWatcher(
                self.config.client()['general']['boot']['agentid'], self.queue)
            gew.watch_issue_closed(call)
         else:
            logging.debug("Client: Skipping request")
