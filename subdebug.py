# Main entry point for the plugin.
# Author: Yuri van Geffen

import sublime, sublime_plugin

import os
import threading
import queue
import asyncore
import socket
from itertools import chain
import re

settings = sublime.load_settings("subdebug")

TCP_IP = '127.0.0.1'
TCP_PORT = 8172
BUFFER_SIZE = 1024

BASEDIR = settings.get("basedir", "")

# Handles incoming and outgoing messages for the MobDebug client
class SubDebugHandler(asyncore.dispatcher):
	def __init__(self, socket, handler_id):
		asyncore.dispatcher.__init__(self, socket)
		self.handler_id = handler_id
		msg_queue.put(b"RUN\n")
		for view_name,row in state_handler.breakpoints():
			msg_queue.put("SETB {0} {1}\n".format(view_name, row).encode('latin-1'))

	# Reads the message-code of incomming messages and passes 
	# them to the right function
	def handle_read(self):
		data = self.recv(BUFFER_SIZE)
		if data:
			print(self.handler_id, "Received: ", data)
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
		self.handler_id = 0
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
			SubDebugHandler(conn_sock, ++self.handler_id)

	def handle_close(self):
		print("Closing server.")
		self.close()

	def handle_error(self):
		self.close()

# Lets the user run the script (until breakpoint)
class RunCommand(sublime_plugin.WindowCommand):
	def run(self):
		print("Running until breakpoint...")
		msg_queue.put(b"RUN\n")

# Lets the user step to the next line
class StepCommand(sublime_plugin.WindowCommand):
	def run(self):
		print("Stepping to next line...")
		msg_queue.put(b"STEP\n")

# Lets the user step to the next line
class SetBreakpointCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		view_name = simplify_path(self.view.file_name())
		row,_ = self.view.rowcol(self.view.sel()[0].begin())
		print("Setting breakpoint:", view_name, row)
		msg_queue.put("SETB {0} {1}\n".format(view_name, row + 1).encode('latin-1'))
		state_handler.set_breakpoint(view_name, row + 1)

# Lets the user pick a base directory from where the lua is executed
class SetBasedirCommand(sublime_plugin.WindowCommand):
	def run(self):
		# Ran if the user want to choose their own base directory
		def choose_other(path):
			global BASEDIR
			path.replace("\\","/")
			BASEDIR = path
			if(BASEDIR[-1] != "/"):
				BASEDIR += "/"
			print("BASEDIR:", BASEDIR)

		# Ran if the user has chosen a base directory option
		def selected_folder(index):
			global BASEDIR
			if index != -1: # The last option lets the user choose a base dir themself
				if(index == len(folders)-1):
					sublime.active_window().show_input_panel("Give the base directory path.", BASEDIR, choose_other, None, None)
				else:
					BASEDIR = folders[index] + "/"
					state_handler.clear_state()
					print("BASEDIR:", BASEDIR)
		folders = list(chain.from_iterable([w.folders() for w in sublime.windows()]))
		folders.insert(len(folders), "Choose other directory...")
		sublime.active_window().show_quick_panel(folders, selected_folder)

#=========Incomming message parsers=========#
# Called when the "202 Paused" message is received
def paused_command(args):
	state_handler.set_line_marker(args[2].decode("utf-8"), int(args[3]))

# Mapping from incomming messages to the functions that parse them
message_parsers = { 
	b"202": paused_command,
}
#===========================================#


class StateHandler():

	# Initiates object by checking which views are available and 
	# clearing the state
	def __init__(self):
		self.clear_state()
		self.update_regions()

	def clear_state(self):
		self.state = {}
		self.update_regions()

	# Gets all available views in sublime and adds the missing ones to the state
	def add_missing_views(self):
		views = [v for v in sum([w.views() for w in sublime.windows()], [])]
		self.views = {simplify_path(v.file_name()):v for v in views if v.file_name() != None}
		print(self.views)
		for view_name, view in self.views.items():
			if view_name not in self.state:
				self.state[view_name] = []

	# Updates all views with the available state-objects using the
	# assigned functions
	def update_regions(self):
		self.add_missing_views()

		# Iterate over all files in the state
		for view_name,regions in self.state.items():
			# Remove all old regions
			for reg_type_name in self.region_types:
				self.views[view_name].erase_regions(reg_type_name)

			region_sets = {}
			# Iterate over all regions in that file
			for (reg_type,line) in regions:
				if reg_type not in region_sets:
					region_sets[reg_type] = []
				region_sets[reg_type].append(sublime.Region(self.views[view_name].text_point(line-1, 0)))
			
			# Register the new regions with sublime
			for reg_name,v in region_sets.items():
				self.views[view_name].add_regions(reg_name, v, *self.region_types[reg_name])

	def set_line_marker(self, view_name, line_number):
		self.add_missing_views()
		if view_name in self.views:
			self.state.setdefault(view_name, [])
			self.state[view_name] = [(k,v) for k, v in self.state[view_name] if k != "line_marker"]
			self.state[view_name].append(("line_marker", line_number))
			self.update_regions()

	def set_breakpoint(self, view_name, line_number):
		self.add_missing_views()
		if view_name in self.views:
			self.state.setdefault(view_name, [])
			self.state[view_name].append(("breakpoint", line_number))
			self.update_regions()

	def breakpoints(self):
		ret = []
		for k,v in self.state.items():
			for t in v:
				if t[0] == "breakpoint":
					ret.append((k,t[1]))
		return ret

	views = {}
	state = {}
	region_types = {
		"breakpoint": ("keyword", "circle"),
		"line_marker": ("keyword", "bookmark"),
	}

def plugin_unloaded():
	settings.set("basedir", BASEDIR)
	print("Closing down the server...")
	server.close()

def simplify_path(path):
	return path.replace("\\","/").replace(BASEDIR,"").split(".")[-2]

# Open a threadsafe message queue
msg_queue = queue.Queue()

state_handler = StateHandler()

# Start listening and open the asyncore loop
server = SubDebugServer(TCP_IP, TCP_PORT)
if os.name == "posix":
	thread = threading.Thread(target=asyncore.loop, kwargs={"use_poll": True})
else:
	thread = threading.Thread(target=asyncore.loop)
thread.start()

