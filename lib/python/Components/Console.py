import enigma
import ctypes
import os
from os import waitpid


class ConsoleItem:
	def __init__(self, containers, cmd, callback, extra_args, binary=False):
		self.extra_args = extra_args
		self.callback = callback
		self.container = enigma.eConsoleAppContainer()
		self.containers = containers
		self.binary = binary
		if isinstance(cmd, str):  # Until .execute supports a better API.
			cmd = [cmd]
		# Create a unique name
		name = cmd[0]
		if name in self.containers:  # Create a unique name.
			name = "%s@%s" % (str(cmd), hex(id(self)))
		self.name = name
		self.containers[name] = self
		# If the caller isn't interested in our results, we don't need
		# to store the output either.
		if callback is not None:
			self.appResults = []
			self.container.dataAvail.append(self.dataAvailCB)
		self.container.appClosed.append(self.finishedCB)
		if len(cmd) > 1:
			print("[Console] Processing command '%s' with arguments %s." % (cmd[0], str(cmd[1:])))
		else:
			print("[Console] Processing command line '%s'." % cmd[0])
		retval = self.container.execute(*cmd)
		if retval:
			self.finishedCB(retval)
		if callback is None:
			pid = self.container.getPID()
			try:
				# print("[Console] Waiting for command (PID %d) to finish." % pid)
				waitpid(pid, 0)
				# print("[Console] Command on PID %d finished." % pid)
			except OSError as err:
				print("[Console] Error %s: Wait for command on PID %d to terminate failed!  (%s)" % (err.errno, pid, err.strerror))

	def dataAvailCB(self, data):
		self.appResults.append(data)

	def finishedCB(self, retval):
		print("[Console] finished:", self.name)
		del self.containers[self.name]
		del self.container.dataAvail[:]
		del self.container.appClosed[:]
		self.container = None
		callback = self.callback
		if callback is not None:
			data = b''.join(self.appResults)
			data = data if self.binary else data.decode()
			callback(data, retval, self.extra_args)


class Console:
	"""
		Console by default will work with strings on callback.
		If binary data required class shoud be initialized with Console(binary=True)
	"""

	def __init__(self, binary=False):
		# Still called appContainers because Network.py accesses it to
		# know if there's still stuff running
		self.appContainers = {}
		self.binary = binary

	def ePopen(self, cmd, callback=None, extra_args=[]):
		print("[Console] command:", cmd)
		return ConsoleItem(self.appContainers, cmd, callback, extra_args, self.binary)

	def eBatch(self, cmds, callback, extra_args=[], debug=False):
		self.debug = debug
		cmd = cmds.pop(0)
		self.ePopen(cmd, self.eBatchCB, [cmds, callback, extra_args])

	def eBatchCB(self, data, retval, _extra_args):
		(cmds, callback, extra_args) = _extra_args
		if self.debug:
			print('[eBatch] retval=%s, cmds left=%d, data:\n%s' % (retval, len(cmds), data))
		if cmds:
			cmd = cmds.pop(0)
			self.ePopen(cmd, self.eBatchCB, [cmds, callback, extra_args])
		else:
			callback(extra_args)

	def kill(self, name):
		if name in self.appContainers:
			print("[Console] killing: ", name)
			self.appContainers[name].container.kill()

	def killAll(self):
		for name, item in self.appContainers.items():
			print("[Console] killing: ", name)
			item.container.kill()
