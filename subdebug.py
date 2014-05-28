# Main entry point for the plugin.
# Author: Yuri van Geffen

import sublime, sublime_plugin

import threading
import queue
import asyncore
import socket

TCP_IP = '127.0.0.1'
TCP_PORT = 8172
BUFFER_SIZE = 1024

# Handles incoming and outgoing messages for the MobDebug client
class SubDebugHandler(asyncore.dispatcher):
	def __init__(self, socket):
		asyncore.dispatcher.__init__(self, socket)
		msg_queue.put(b"STEP\n")

	# Reads the message-code of incomming messages and passes 
	# them to the right function
	def handle_read(self):
		data = self.recv(BUFFER_SIZE)
		if data:
			print("Received: ", data)
			split = data.split()
			if split[0] in message_parsers:
				message_parsers[split[0]](split)

	def handle_write(self):
		if not msg_queue.empty():
			msg = msg_queue.get()
			print("Sending: ", msg)
			self.send(msg)

	def handle_error(self):
		raise

# Starts listening on TCP_PORT and accepts incoming connections
# before passing them to an instance of SubDebugHandler
class SubDebugServer(asyncore.dispatcher):

	def __init__(self, host, port):
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind((host, port))
		self.listen(1)
		print("Started listening on: ", host, ":", port)

	def handle_accept(self):
		pair = self.accept()
		if pair is not None:
			(conn_sock, client_address) = pair
			print("Incoming connection: ", client_address)
			SubDebugHandler(conn_sock)

	def handle_close(self):
		print("Closing server.")
		self.close()

	def handle_error(self):
		self.close()

# Lets the user step to the next line
class StepCommand(sublime_plugin.WindowCommand):
	def run(self):
		print("Stepping to next line...")
		msg_queue.put(b"STEP\n")


#=========Incomming message parsers=========#

# Called when the "202 Paused" message is received
def paused_command(args):
	reg = sublime.Region(int(args[3]), int(args[3]))
	views = [v for v in sum([w.views() for w in sublime.windows()], [])]
		#name = v.file_name().split("\\")
	views = [v for v in views if v.file_name().split("\\")[-1] == args[2].decode("utf-8")]
	print(len(views))

	#view = [v for v in sum([w.views() for w in sublime.windows()], []) if v.name() == args[2].decode("utf-8")]

	views[0].add_regions("test", [reg], "keyword", "dot")

# Mapping from incomming messages to the functions that parse them
message_parsers = { 
	b"202": paused_command,
}

#===========================================#

# Open a threadsafe message queue
msg_queue = queue.Queue()

# Start listening and open the asyncore loop
server = SubDebugServer(TCP_IP, TCP_PORT)
thread = threading.Thread(target=asyncore.loop)
thread.start()
