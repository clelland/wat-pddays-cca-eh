#!/usr/bin/python
import sys, json, random, string
import xmpp

################################################################################

SERVER = 'gcm.googleapis.com'
PORT = 5235
USERNAME = '90031296475'
PASSWORD = 'AIzaSyBa5T4FvOUgxKLHyzTf13FLw9UU02GR3Lc'

unacked_messages_quota = 1000
send_queue = []
client = None

connected_users = {}

################################################################################

# Return a random alphanumerical id
def random_id():
  rid = ''
  for x in range(8): rid += random.choice(string.ascii_letters + string.digits)
  return rid

################################################################################

def add_user(regid, name):
  connected_users[regid] = name

################################################################################

def sendUpdatedListOfClientsToClients():
  for (regid,name) in connected_users.iteritems():
    send_queue.append({
      'to': regid,
      'message_id': random_id(),
      'data': {
        'type': 'userListChangeEh',
        'users': filter(lambda (r,n): r != regid, connected_users.items())
      }
    })

################################################################################

def sendIncomingEh(from_userid, to_userid):
  send_queue.append({
    'to': to_userid,
    'message_id': random_id(),
    'data': {
      'type': 'incomingEh',
      'from_userid': from_userid
    }
  })

################################################################################

def send(json_dict):
  template = "<message><gcm xmlns='google:mobile:data'>{1}</gcm></message>"
  content = template.format(client.Bind.bound[0], json.dumps(json_dict))
  client.send(xmpp.protocol.Message(node = content))
  #print "Sent: " + json.dumps(json_dict, indent=2)

################################################################################

def flush_queued_messages():
  global unacked_messages_quota
  while len(send_queue) and unacked_messages_quota > 0:
    send(send_queue.pop(0))
    unacked_messages_quota -= 1

################################################################################

def message_callback(session, message):
  global unacked_messages_quota
  gcm = message.getTags('gcm')
  if not gcm:
    return
  msg = json.loads(gcm[0].getData())

  if msg.has_key('message_type') and (msg['message_type'] == 'ack' or msg['message_type'] == 'nack'):
    unacked_messages_quota += 1
    return

  # Acknowledge the incoming message immediately.
  send({
    'to': msg['from'],
    'message_type': 'ack',
    'message_id': msg['message_id']
  })

  if not msg.has_key('data'):
    print "WARNING: No Payload!"
    return

  payload = None
  if (msg['data'].has_key('payload')):
    payload = json.loads(msg['data']['payload'])
  else:
    payload = msg

  # Is this the crspec gcm call?
  if payload['data'].has_key('test'):
    # Send a dummy echo response back to the app that sent the upstream message.
    send_queue.append({
      'to': msg['from'],
      'message_id': random_id(),
      'data': {
         'pong': msg['message_id']
      }
    })
    return

  #print "Got: " + json.dumps(payload, indent=2)

  msg_type = payload['data']['type']
  if msg_type == 'identifySelfEh':
    # Add this user to the list of actives
    # TODO: how to prune users? (Perhaps after they fail to ack a message?)
    add_user(msg['from'], payload['data']['name'])
    sendUpdatedListOfClientsToClients()
  elif msg_type == 'sendEh':
    sendIncomingEh(msg['from'], payload['data']['to_userid'])


################################################################################

def main():
  global client
  client = xmpp.Client('gcm.googleapis.com', debug=['socket'])
  client.connect(server=(SERVER,PORT), secure=1, use_srv=False)
  auth = client.auth(USERNAME, PASSWORD)

  if not auth:
    print 'Authentication failed!'
    sys.exit(1)

  client.RegisterHandler('message', message_callback)

  while True:
    client.Process(1)
    flush_queued_messages()

################################################################################

if __name__ == '__main__':
  main()
