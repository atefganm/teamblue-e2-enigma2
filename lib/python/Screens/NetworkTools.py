import time
from os import remove, rename, popen, listdir, system
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from Components.About import getEnigmaVersionString
from Components.Console import Console
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.Input import Input
from Screens.InputBox import InputBox
from Components.ScrollLabel import ScrollLabel
from Components.Pixmap import Pixmap, MultiPixmap
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigIP, ConfigText, ConfigPassword, ConfigSelection, ConfigNumber, ConfigLocations, NoSave, ConfigMacText
from Components.Pixmap import Pixmap, MultiPixmap
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.FileList import MultiFileSelectList
from Tools.Directories import fileExists
from boxbranding import getMachineBrand, getMachineName, getBoxType
from subprocess import call
import subprocess
import six
import glob
import sys

basegroup = "packagegroup-base"


class NetworkNfs(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("NFS Setup"))
		self.skinName = "NetworkNfs"
		self.onChangedEntry = []
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_green'] = Label(_("Start"))
		self['key_red'] = Label(_("Remove Service"))
		self['key_yellow'] = Label(_("Autostart"))
		self['lab4'] = Label(_("active NFS Shares:"))
		self['key_blue'] = Label((" "))
		self['lab3'] = Label((" "))
		self.Console = Console()
		self.my_nfs_active = False
		self.my_nfs_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.UninstallCheck, 'green': self.NfsStartStop, 'yellow': self.Nfsset, 'blue': self.NfsExportOnOff})
		self.service_name = basegroup + '-nfs'
		self.NfsExportCheck()
		self.onLayoutFinish.append(self.InstallCheck)

	def InstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if 'Collected errors' in str:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is in progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif not str:
			self.feedscheck = self.session.open(MessageBox, _('Please wait while feeds state is checked.'), MessageBox.TYPE_INFO, enable_input=False)
			self.feedscheck.setTitle(_('Checking Feeds'))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			self.updateService()

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		result = six.ensure_str(result)
		if 'bad address' in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ('wget returned 1' or 'wget returned 255' or '404 Not Found') in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _('Your %s %s will be restarted after the installation of service.\nReady to install %s ?') % (getMachineBrand(), getMachineName(), self.service_name), MessageBox.TYPE_YESNO)

	def InstallPackage(self, val):
		if val:
			self.doInstall(self.installComplete, self.service_name)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname, callback)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.session.open(TryQuitMainloop, 2)

	def UninstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		if str:
			restartbox = self.session.openWithCallback(self.RemovePackage, MessageBox, _('Your %s %s will be restarted after the removal of service.\nDo you want to remove now ?') % (getMachineBrand(), getMachineName()), MessageBox.TYPE_YESNO)
			restartbox.setTitle(_('Ready to remove %s ?') % self.service_name)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove', callback)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.session.open(TryQuitMainloop, 2)

	def createSummary(self):
		return NetworkServicesSummary

	def NfsStartStop(self):
		if not self.my_nfs_run:
			self.Console.ePopen('/etc/init.d/nfsserver start', self.StartStopCallback)
		elif self.my_nfs_run:
			self.Console.ePopen('/etc/init.d/nfsserver stop', self.StartStopCallback)

	def NfsExportCheck(self):
		self.Console.ePopen('/usr/sbin/exportfs -ua')
		time.sleep(1)
		self.Console.ePopen('/usr/sbin/exportfs -ra')
		time.sleep(1)
		if fileExists('/etc/exports'):
			exports = popen('/usr/sbin/exportfs').read()
			if exports == "":
				self['lab3'].setText(_("no valid entrys in /etc/exports found\nPress blue button to activate default Enigma2\nHDD and USB as NFS exports,\nif valid mounted hardware is available."))
				self['key_blue'].setText(_("NFS Shares ON"))
			else:
				self['lab3'].setText(exports)
				self['key_blue'].setText(_("NFS Shares OFF"))
		else:
			self['lab3'].setText(_("No '/etc/exports' Configuration File found.\nPress blue button to activate default Enigma2\nHDD and USB as NFS exports, if the hardware is available."))
			self['key_blue'].setText(_("NFS Shares ON"))

	def NfsExportOnOff(self):
		if fileExists('/etc/exports') and popen('/usr/sbin/exportfs').read() != "":
			self.message = self.session.open(MessageBox, _("please wait\nwhile deacticate NFS exports"), MessageBox.TYPE_INFO, 5)
			self.message.setTitle(_('Info'))
			self.Console.ePopen('/usr/sbin/exportfs -ua')
			self.Console.ePopen('rm /etc/exports && touch /etc/exports')
			self['lab3'].setText(_("No '/etc/exports' Configuration File found.\nPress blue button to activate default Enigma2\nHDD and USB as NFS exports, if the hardware is available."))
			self['key_blue'].setText(_("NFS Shares ON"))
		else:
			self.message = self.session.open(MessageBox, _("please wait\nwhile acticate NFS exports"), MessageBox.TYPE_INFO, 5)
			self.message.setTitle(_("Info"))
			netz = popen('ip route show |grep "/" |cut -d " " -f 0').read().strip()
			opt = "(sync,no_subtree_check,rw)"
			i = 0
			z = listdir("/media")
			h = open("/etc/exports", "w")
			while i < len(z):
				if z[i] != "autofs" and z[i] != "net":
					h.write("/media/" + str(z[i]) + " " + netz + opt + "\n")
				i = i + 1
			h.close()
			self.Console.ePopen('/usr/sbin/exportfs -ra')
		self.NfsExportCheck()

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def Nfsset(self):
		if fileExists('/etc/rc2.d/S13nfsserver'):
			self.Console.ePopen('update-rc.d -f nfsserver remove', self.StartStopCallback)
		else:
			self.Console.ePopen('update-rc.d -f nfsserver defaults 13', self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		nfs_process = str(p.named('nfsd')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_nfs_active = False
		self.my_nfs_run = False
		if fileExists('/etc/rc2.d/S13nfsserver'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_nfs_active = True
		if nfs_process:
			self.my_nfs_run = True
		if self.my_nfs_run:
			self['labstop'].hide()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['lab2'].text + ' ' + self['labrun'].text
		else:
			self['labstop'].show()
			self['labrun'].hide()
			self['key_green'].setText(_("Start"))
			status_summary = self['lab2'].text + ' ' + self['labstop'].text
		title = _("NFS Setup")
		autostartstatus_summary = self['lab1'].text + ' ' + self['labactive'].text

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


class NetworkSamba(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Samba Setup"))
		self.skinName = "NetworkSamba"
		self.onChangedEntry = []
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_green'] = Label(_("Start"))
		self['key_red'] = Label(_("Remove Service"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label(_("Show Log"))
		self.Console = Console()
		self.my_Samba_active = False
		self.my_Samba_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.UninstallCheck, 'green': self.SambaStartStop, 'yellow': self.activateSamba, 'blue': self.Sambashowlog})
		self.service_name = basegroup + '-smbfs-server'
		self.onLayoutFinish.append(self.InstallCheck)

	def InstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if 'Collected errors' in str:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is in progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif not str:
			self.feedscheck = self.session.open(MessageBox, _('Please wait while feeds state is checked.'), MessageBox.TYPE_INFO, enable_input=False)
			self.feedscheck.setTitle(_('Checking Feeds'))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			self.updateService()

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		result = six.ensure_str(result)
		if 'bad address' in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ('wget returned 1' or 'wget returned 255' or '404 Not Found') in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.QuestionCallback, MessageBox, _('Your %s %s will be restarted after the installation of service.\nReady to install %s ?') % (getMachineBrand(), getMachineName(), self.service_name), MessageBox.TYPE_YESNO)

	def QuestionCallback(self, val):
		if val:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _('Do you want to also install samba client?\nThis allows you to mount your windows shares on this device.'), MessageBox.TYPE_YESNO)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackage(self, val):
		if val:
			self.service_name = self.service_name + ' ' + basegroup + '-smbfs-client'
		self.doInstall(self.installComplete, self.service_name)

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname, callback)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.session.open(TryQuitMainloop, 2)

	def UninstallCheck(self):
		self.service_name = self.service_name + ' ' + basegroup + '-smbfs-client'
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		if str:
			restartbox = self.session.openWithCallback(self.RemovePackage, MessageBox, _('Your %s %s will be restarted after the removal of service.\nDo you want to remove now ?') % (getMachineBrand(), getMachineName()), MessageBox.TYPE_YESNO)
			restartbox.setTitle(_('Ready to remove %s ?') % self.service_name)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove', callback)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.session.open(TryQuitMainloop, 2)

	def createSummary(self):
		return NetworkServicesSummary

	def Sambashowlog(self):
		self.session.open(NetworkSambaLog)

	def SambaStartStop(self):
		commands = []
		if not self.my_Samba_run:
			subprocess.append('/etc/init.d/samba start')
		elif self.my_Samba_run:
			subprocess.append('/etc/init.d/samba stop')
			subprocess.append('killall nmbd')
			subprocess.append('killall smbd')
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def activateSamba(self):
		commands = []
		if fileExists('/etc/rc2.d/S20samba'):
			subprocess.append('update-rc.d -f samba remove')
		else:
			subprocess.append('update-rc.d -f samba defaults')
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def updateService(self):
		import process
		p = process.ProcessList()
		samba_process = str(p.named('smbd')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_Samba_active = False
		if fileExists('/etc/rc2.d/S20samba'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_Samba_active = True

		self.my_Samba_run = False

		if samba_process:
			self.my_Samba_run = True

		if self.my_Samba_run:
			self['labstop'].hide()
			self['labactive'].show()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['lab2'].text + ' ' + self['labrun'].text
		else:
			self['labrun'].hide()
			self['labstop'].show()
			self['labactive'].show()
			self['key_green'].setText(_("Start"))
			status_summary = self['lab2'].text + ' ' + self['labstop'].text
		title = _("Samba Setup")
		autostartstatus_summary = self['lab1'].text + ' ' + self['labactive'].text

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


class NetworkSambaLog(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Samba Log"))
		self.skinName = "NetworkLog"
		self['infotext'] = ScrollLabel('')
		self.Console = Console()
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'up': self['infotext'].pageUp, 'down': self['infotext'].pageDown})
		smbdview = ''
		nmbdview = ''
		if fileExists('/var/volatile/log/log.smbd'):
			self.Console.ePopen('tail -n20 /var/volatile/log/log.smbd > /tmp/tmp.smbd.log')
			time.sleep(1)
			f = open('/tmp/tmp.smbd.log', 'r')
			for line in f.readlines():
				smbdview += line
			f.close()
			if smbdview == "":
				smbdview = _("no log entrys") + "\n\n\n\n\n"
			remove('/tmp/tmp.smbd.log')
		else:
			smbdview = _("no") + " log.smbd " + _("found")

		if fileExists('/var/volatile/log/log.nmbd'):
			self.Console.ePopen('tail -n20 /var/volatile/log/log.nmbd > /tmp/tmp.nmbd.log')
			time.sleep(1)
			f = open('/tmp/tmp.nmbd.log', 'r')
			for line in f.readlines():
				nmbdview += line
			f.close()
			if nmbdview == "":
				nmbdview = _("no log entrys")
			remove('/tmp/tmp.nmbd.log')
		else:
			nmbdview = _("no") + " log.nmbd " + _("found")
		sambaview = "--/var/volatile/log/log.smbd:\n" + smbdview + "\n--/var/volatile/log/log.nmbd:\n" + nmbdview
		self['infotext'].setText(sambaview)


class NetworkAfp(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("AFP Setup"))
		self.skinName = "NetworkAfp"
		self.onChangedEntry = []
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_red'] = Label(_("Remove Service"))
		self['key_green'] = Label(_("Start"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label()
		self['status_summary'] = StaticText()
		self['autostartstatus_summary'] = StaticText()
		self.Console = Console()
		self.my_afp_active = False
		self.my_afp_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.UninstallCheck, 'green': self.AfpStartStop, 'yellow': self.activateAfp})
		self.service_name = basegroup + '-appletalk netatalk'
		self.onLayoutFinish.append(self.InstallCheck)

	def InstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if 'Collected errors' in str:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is in progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif not str:
			self.feedscheck = self.session.open(MessageBox, _('Please wait while feeds state is checked.'), MessageBox.TYPE_INFO, enable_input=False)
			self.feedscheck.setTitle(_('Checking Feeds'))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			self.updateService()

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		result = six.ensure_str(result)
		if 'bad address' in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ('wget returned 1' or 'wget returned 255' or '404 Not Found') in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _('Your %s %s will be restarted after the installation of service\nReady to install %s ?') % (getMachineBrand(), getMachineName(), self.service_name), MessageBox.TYPE_YESNO)

	def InstallPackage(self, val):
		if val:
			self.doInstall(self.installComplete, self.service_name)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname, callback)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.session.open(TryQuitMainloop, 2)

	def UninstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if str:
			restartbox = self.session.openWithCallback(self.RemovePackage, MessageBox, _('Your %s %s will be restarted after the removal of service\nDo you want to remove now ?') % (getMachineBrand(), getMachineName()), MessageBox.TYPE_YESNO)
			restartbox.setTitle(_('Ready to remove %s ?') % self.service_name)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove', callback)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.session.open(TryQuitMainloop, 2)

	def createSummary(self):
		return NetworkServicesSummary

	def AfpStartStop(self):
		if not self.my_afp_run:
			self.Console.ePopen('/etc/init.d/atalk start', self.StartStopCallback)
		elif self.my_afp_run:
			self.Console.ePopen('/etc/init.d/atalk stop', self.StartStopCallback)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def activateAfp(self):
		if fileExists('/etc/rc2.d/S20atalk'):
			self.Console.ePopen('update-rc.d -f atalk remove', self.StartStopCallback)
		else:
			self.Console.ePopen('update-rc.d -f atalk defaults', self.StartStopCallback)

	def updateService(self, result=None, retval=None, extra_args=None):
		import process
		p = process.ProcessList()
		afp_process = str(p.named('afpd')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_afp_active = False
		self.my_afp_run = False
		if fileExists('/etc/rc2.d/S20atalk'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_afp_active = True
		if afp_process:
			self.my_afp_run = True
		if self.my_afp_run:
			self['labstop'].hide()
			self['labactive'].show()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['lab2'].text + ' ' + self['labrun'].text
		else:
			self['labrun'].hide()
			self['labstop'].show()
			self['labactive'].show()
			self['key_green'].setText(_("Start"))
			status_summary = self['lab2'].text + ' ' + self['labstop'].text
		title = _("AFP Setup")
		autostartstatus_summary = self['lab1'].text + ' ' + self['labactive'].text

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)
######################################################################################################################


class NetworkSABnzbd(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("SABnzbd Setup"))
		self.skinName = "NetworkSABnzbd"
		self.onChangedEntry = []
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_red'] = Label(_("Remove Service"))
		self['key_green'] = Label(_("Start"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label()
		self['status_summary'] = StaticText()
		self['autostartstatus_summary'] = StaticText()
		self.Console = Console()
		self.my_sabnzbd_active = False
		self.my_sabnzbd_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.UninstallCheck, 'green': self.SABnzbStartStop, 'yellow': self.activateSABnzbd})
		self.service_name = ("sabnzbd3")
		self.checkSABnzbdService()

	def checkSABnzbdService(self):
		print('INSTALL CHECK STARTED', self.service_name)
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		str = six.ensure_str(str)
		print('INSTALL CHECK FINISHED', str)
		if not str:
			self.feedscheck = self.session.open(MessageBox, _('Please wait while feeds state is checked.'), MessageBox.TYPE_INFO, enable_input=False)
			self.feedscheck.setTitle(_('Checking Feeds'))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			print('INSTALL ALREADY INSTALLED')
			self.updateService()

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		result = six.ensure_str(result)
		if (float(getEnigmaVersionString()) < 3.0 and result.find('mipsel/Packages.gz, wget returned 1') != -1) or (float(getEnigmaVersionString()) >= 3.0 and result.find('mips32el/Packages.gz, wget returned 1') != -1):
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif result.find('bad address') != -1:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _('Ready to install %s ?') % self.service_name, MessageBox.TYPE_YESNO)

	def InstallPackage(self, val):
		if val:
			self.doInstall(self.installComplete, self.service_name)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname, callback)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.feedscheck.close()
		self.updateService()

	def UninstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if str:
			self.session.openWithCallback(self.RemovePackage, MessageBox, _('Ready to remove %s ?') % self.service_name, MessageBox.TYPE_YESNO)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove', callback)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.updateService()

	def createSummary(self):
		return NetworkServicesSummary

	def SABnzbStartStop(self):
		if not self.my_sabnzbd_run:
			self.Console.ePopen('/etc/init.d/sabnzbd start')
			time.sleep(3)
			self.updateService()
		elif self.my_sabnzbd_run:
			self.Console.ePopen('/etc/init.d/sabnzbd stop')
			time.sleep(3)
			self.updateService()

	def activateSABnzbd(self):
		if fileExists('/etc/rc2.d/S20sabnzbd'):
			self.Console.ePopen('update-rc.d -f sabnzbd remove')
		else:
			self.Console.ePopen('update-rc.d -f sabnzbd defaults')
		time.sleep(3)
		self.updateService()

	def updateService(self, result=None, retval=None, extra_args=None):
		import process
		p = process.ProcessList()
		sabnzbd_process = str(p.named('SABnzbd.py')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_sabnzbd_active = False
		self.my_sabnzbd_run = False
		if fileExists('/etc/rc2.d/S20sabnzbd'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_sabnzbd_active = True
		if sabnzbd_process:
			self.my_sabnzbd_run = True
		if self.my_sabnzbd_run:
			self['labstop'].hide()
			self['labactive'].show()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['lab2'].text + ' ' + self['labrun'].text
		else:
			self['labrun'].hide()
			self['labstop'].show()
			self['labactive'].show()
			self['key_green'].setText(_("Start"))
			status_summary = self['lab2'].text + ' ' + self['labstop'].text
		title = _("SABnzbd Setup")
		autostartstatus_summary = self['lab1'].text + ' ' + self['labactive'].text

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

#########################################################################################################


class NetworkFtp(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("FTP Setup"))
		self.skinName = "NetworkFTP"
		self.onChangedEntry = []
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_green'] = Label(_("Start"))
		self['key_yellow'] = Label(_("Autostart"))
		self.Console = Console()
		self.my_ftp_active = False
		self.my_ftp_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'green': self.FtpStartStop, 'yellow': self.activateFtp})
		self.Console = Console()
		self.onLayoutFinish.append(self.updateService)

	def createSummary(self):
		return NetworkServicesSummary

	def FtpStartStop(self):
		commands = []
		if not self.my_ftp_run:
			commands.append('/etc/init.d/vsftpd start')
		elif self.my_ftp_run:
			commands.append('/etc/init.d/vsftpd stop')
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def activateFtp(self):
		commands = []
		if len(glob.glob('/etc/rc2.d/S*0vsftpd')):
		#if fileExists('/etc/rc2.d/S20vsftpd'):
			commands.append('update-rc.d -f vsftpd remove')
		else:
			commands.append('update-rc.d -f vsftpd defaults')
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def updateService(self):
		import process
		p = process.ProcessList()
		ftp_process = str(p.named('vsftpd')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_ftp_active = False
		if len(glob.glob('/etc/rc2.d/S*0vsftpd')):
		#if fileExists('/etc/rc2.d/S20vsftpd'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_ftp_active = True

		self.my_ftp_run = False
		if ftp_process:
			self.my_ftp_run = True
		if self.my_ftp_run:
			self['labstop'].hide()
			self['labactive'].show()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['lab2'].text + ' ' + self['labrun'].text
		else:
			self['labrun'].hide()
			self['labstop'].show()
			self['labactive'].show()
			self['key_green'].setText(_("Start"))
			status_summary = self['lab2'].text + ' ' + self['labstop'].text
		title = _("FTP Setup")
		autostartstatus_summary = self['lab1'].text + ' ' + self['labactive'].text

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


class NetworkOpenvpn(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("OpenVpn Setup"))
		self.skinName = "NetworkOpenvpn"
		self.onChangedEntry = []
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['labconfig'] = Label(_("Config file name (ok to change):"))
		self['labconfigfilename'] = Label(_("default"))
		self.config_file = ""
		self['key_green'] = Label(_("Start"))
		self['key_red'] = Label(_("Remove Service"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label(_("Show Log"))
		self.Console = Console()
		self.my_vpn_active = False
		self.my_vpn_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.inputconfig, 'back': self.close, 'red': self.UninstallCheck, 'green': self.VpnStartStop, 'yellow': self.activateVpn, 'blue': self.Vpnshowlog})
		self.service_name = 'openvpn'
		self.onLayoutFinish.append(self.InstallCheck)

	def InstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if 'Collected errors' in str:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is in progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif not str:
			self.feedscheck = self.session.open(MessageBox, _('Please wait while feeds state is checked.'), MessageBox.TYPE_INFO, enable_input=False)
			self.feedscheck.setTitle(_('Checking Feeds'))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			self.updateService()

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		result = six.ensure_str(result)
		if 'bad address' in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ('wget returned 1' or 'wget returned 255' or '404 Not Found') in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _('Ready to install %s ?') % self.service_name, MessageBox.TYPE_YESNO)

	def InstallPackage(self, val):
		if val:
			self.doInstall(self.installComplete, self.service_name)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname, callback)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.feedscheck.close()
		self.updateService()

	def UninstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if str:
			self.session.openWithCallback(self.RemovePackage, MessageBox, _('Ready to remove %s ?') % self.service_name, MessageBox.TYPE_YESNO)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove', callback)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.close()

	def createSummary(self):
		return NetworkServicesSummary

	def Vpnshowlog(self):
		self.session.open(NetworkVpnLog)

	def VpnStartStop(self):
		if not self.my_vpn_run:
			self.Console.ePopen('/etc/init.d/openvpn start ' + self.config_file, self.StartStopCallback)
		elif self.my_vpn_run:
			self.Console.ePopen('/etc/init.d/openvpn stop', self.StartStopCallback)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def activateVpn(self):
		if fileExists('/etc/rc2.d/S20openvpn'):
			self.Console.ePopen('update-rc.d -f openvpn remove', self.StartStopCallback)
		else:
			self.Console.ePopen('update-rc.d -f openvpn defaults', self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		openvpn_process = str(p.named('openvpn')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_Vpn_active = False
		self.my_vpn_run = False
		if fileExists('/etc/rc2.d/S20openvpn'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_Vpn_active = True
		if openvpn_process:
			self.my_vpn_run = True
		if self.my_vpn_run:
			self['labstop'].hide()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['lab2'].text + ' ' + self['labrun'].text
		else:
			self['labstop'].show()
			self['labrun'].hide()
			self['key_green'].setText(_("Start"))
			status_summary = self['lab2'].text + ' ' + self['labstop'].text
		title = _("OpenVpn Setup")
		autostartstatus_summary = self['lab1'].text + ' ' + self['labactive'].text

		self['labconfig'].show()

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

	def inputconfig(self):
		self.session.openWithCallback(self.askForWord, InputBox, title=_("Input config file name:"), text=" " * 20, maxSize=20, type=Input.TEXT)

	def askForWord(self, word):
		if word is None:
			pass
		else:
			self.config_file = _(word)
			self['labconfigfilename'].setText(self.config_file)


class NetworkVpnLog(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("OpenVpn Log"))
		self.skinName = "NetworkInadynLog"
		self['infotext'] = ScrollLabel('')
		self.Console = Console()
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'up': self['infotext'].pageUp, 'down': self['infotext'].pageDown})
		strview = ''
		self.Console.ePopen('tail /etc/openvpn/openvpn.log > /etc/openvpn/tmp.log')
		time.sleep(1)
		if fileExists('/etc/openvpn/tmp.log'):
			f = open('/etc/openvpn/tmp.log', 'r')
			for line in f.readlines():
				strview += line
			f.close()
			remove('/etc/openvpn/tmp.log')
		self['infotext'].setText(strview)


class NetworkSambaLog(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Samba Log"))
		self.skinName = "NetworkInadynLog"
		self['infotext'] = ScrollLabel('')
		self.Console = Console()
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'up': self['infotext'].pageUp, 'down': self['infotext'].pageDown})
		strview = ''
		self.Console.ePopen('tail /tmp/smb.log > /tmp/tmp.log')
		time.sleep(1)
		if fileExists('/tmp/tmp.log'):
			f = open('/tmp/tmp.log', 'r')
			for line in f.readlines():
				strview += line
			f.close()
			remove('/tmp/tmp.log')
		self['infotext'].setText(strview)


class NetworkTelnet(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Telnet Setup"))
		self.skinName = "NetworkTelnet"
		self.onChangedEntry = []
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_green'] = Label(_("Start"))
		self['key_red'] = Label(_("Remove Service"))
		self['key_yellow'] = Label(_("Autostart"))
		self.Console = Console()
		self.my_telnet_active = False
		self.my_telnet_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'green': self.TelnetStartStop, 'yellow': self.activateTelnet})

	def createSummary(self):
		return NetworkServicesSummary

	def TelnetStartStop(self):
		commands = []
		if fileExists('/etc/init.d/telnetd.busybox'):
			if self.my_telnet_run:
				commands.append('/etc/init.d/telnetd.busybox stop')
			else:
				commands.append('/bin/su -l -c "/etc/init.d/telnetd.busybox start"')
			self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def activateTelnet(self):
		commands = []
		if fileExists('/etc/init.d/telnetd.busybox'):
			if fileExists('/etc/rc2.d/S20telnetd.busybox'):
				commands.append('update-rc.d -f telnetd.busybox remove')
			else:
				commands.append('update-rc.d -f telnetd.busybox defaults')
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def updateService(self):
		import process
		p = process.ProcessList()
		telnet_process = str(p.named('telnetd')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_telnet_active = False
		self.my_telnet_run = False
		if fileExists('/etc/rc2.d/S20telnetd.busybox'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_telnet_active = True

		if telnet_process:
			self.my_telnet_run = True
		if self.my_telnet_run:
			self['labstop'].hide()
			self['labactive'].show()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['lab2'].text + ' ' + self['labrun'].text
		else:
			self['labrun'].hide()
			self['labstop'].show()
			self['labactive'].show()
			self['key_green'].setText(_("Start"))
			status_summary = self['lab2'].text + ' ' + self['labstop'].text
		title = _("Telnet Setup")
		autostartstatus_summary = self['lab1'].text + ' ' + self['labactive'].text

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


class NetworkInadyn(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Inadyn Setup"))
		self.onChangedEntry = []
		self['autostart'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Active")))
		self['labdisabled'] = Label(_(_("Disabled")))
		self['status'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['time'] = Label(_("Time Update in Minutes:"))
		self['labtime'] = Label()
		self['username'] = Label(_("Username") + ":")
		self['labuser'] = Label()
		self['password'] = Label(_("Password") + ":")
		self['labpass'] = Label()
		self['alias'] = Label(_("Alias") + ":")
		self['labalias'] = Label()
		self['sactive'] = Pixmap()
		self['sinactive'] = Pixmap()
		self['system'] = Label(_("System") + ":")
		self['labsys'] = Label()
		self['key_red'] = Label(_("Remove Service"))
		self['key_green'] = Label(_("Start"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label(_("Show Log"))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions', 'SetupActions'], {'ok': self.setupinadyn, 'back': self.close, 'menu': self.setupinadyn, 'red': self.UninstallCheck, 'green': self.InadynStartStop, 'yellow': self.autostart, 'blue': self.inaLog})
		self.Console = Console()
		self.service_name = 'inadyn-mt'
		self.onLayoutFinish.append(self.InstallCheck)

	def InstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if 'Collected errors' in str:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is in progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif not str:
			self.feedscheck = self.session.open(MessageBox, _('Please wait while feeds state is checked.'), MessageBox.TYPE_INFO, enable_input=False)
			self.feedscheck.setTitle(_('Checking Feeds'))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			self.updateService()

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		result = six.ensure_str(result)
		if 'bad address' in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ('wget returned 1' or 'wget returned 255' or '404 Not Found') in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _('Ready to install %s ?') % self.service_name, MessageBox.TYPE_YESNO)

	def InstallPackage(self, val):
		if val:
			self.doInstall(self.installComplete, self.service_name)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname, callback)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.feedscheck.close()
		self.updateService()

	def UninstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if str:
			self.session.openWithCallback(self.RemovePackage, MessageBox, _('Ready to remove %s ?') % self.service_name, MessageBox.TYPE_YESNO)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove', callback)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.close()

	def createSummary(self):
		return NetworkServicesSummary

	def InadynStartStop(self):
		if not self.my_inadyn_run:
			self.Console.ePopen('/etc/init.d/inadyn-mt start', self.StartStopCallback)
		elif self.my_inadyn_run:
			self.Console.ePopen('/etc/init.d/inadyn-mt stop', self.StartStopCallback)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def autostart(self):
		if fileExists('/etc/rc2.d/S20inadyn-mt'):
			self.Console.ePopen('update-rc.d -f inadyn-mt remove', self.StartStopCallback)
		else:
			self.Console.ePopen('update-rc.d -f inadyn-mt defaults', self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		inadyn_process = str(p.named('inadyn-mt')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].hide()
		self['labdisabled'].hide()
		self['sactive'].hide()
		self.my_inadyn_active = False
		self.my_inadyn_run = False
		if fileExists('/etc/rc2.d/S20inadyn-mt'):
			self['labdisabled'].hide()
			self['labactive'].show()
			self.my_inadyn_active = True
			autostartstatus_summary = self['autostart'].text + ' ' + self['labactive'].text
		else:
			self['labactive'].hide()
			self['labdisabled'].show()
			autostartstatus_summary = self['autostart'].text + ' ' + self['labdisabled'].text
		if inadyn_process:
			self.my_inadyn_run = True
		if self.my_inadyn_run:
			self['labstop'].hide()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['status'].text + ' ' + self['labrun'].text
		else:
			self['labstop'].show()
			self['labrun'].hide()
			self['key_green'].setText(_("Start"))
			status_summary = self['status'].text + ' ' + self['labstop'].text

		#self.my_nabina_state = False
		if fileExists('/etc/inadyn.conf'):
			f = open('/etc/inadyn.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('username '):
					line = line[9:]
					self['labuser'].setText(line)
				elif line.startswith('password '):
					line = line[9:]
					self['labpass'].setText(line)
				elif line.startswith('alias '):
					line = line[6:]
					self['labalias'].setText(line)
				elif line.startswith('update_period_sec '):
					line = line[18:]
					line = (int(line) / 60)
					self['labtime'].setText(str(line))
				elif line.startswith('dyndns_system ') or line.startswith('#dyndns_system '):
					if line.startswith('#'):
						line = line[15:]
						self['sactive'].hide()
					else:
						line = line[14:]
						self['sactive'].show()
					self['labsys'].setText(line)
			f.close()
		title = _("Inadyn Setup")

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

	def setupinadyn(self):
		self.session.openWithCallback(self.updateService, NetworkInadynSetup)

	def inaLog(self):
		self.session.open(NetworkInadynLog)


class NetworkInadynSetup(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.selectionChanged)
		Screen.setTitle(self, _("Inadyn Setup"))
		self['key_red'] = Label(_("Save"))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions', 'VirtualKeyboardActions'], {'red': self.saveIna, 'back': self.close, 'showVirtualKeyboard': self.KeyText})
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.updateList()
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["config"].getCurrent()
		if item:
			name = str(item[0])
			desc = str(item[1].value)
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def updateList(self):
		self.ina_user = NoSave(ConfigText(fixed_size=False))
		self.ina_pass = NoSave(ConfigText(fixed_size=False))
		self.ina_alias = NoSave(ConfigText(fixed_size=False))
		self.ina_period = NoSave(ConfigNumber())
		self.ina_sysactive = NoSave(ConfigYesNo(default='False'))
		self.ina_system = NoSave(ConfigSelection(default="dyndns@dyndns.org", choices=[("dyndns@dyndns.org", "dyndns@dyndns.org"), ("statdns@dyndns.org", "statdns@dyndns.org"), ("custom@dyndns.org", "custom@dyndns.org"), ("default@no-ip.com", "default@no-ip.com")]))

		if fileExists('/etc/inadyn.conf'):
			f = open('/etc/inadyn.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('username '):
					line = line[9:]
					self.ina_user.value = line
					ina_user1 = (_("Username") + ":", self.ina_user)
					self.list.append(ina_user1)
				elif line.startswith('password '):
					line = line[9:]
					self.ina_pass.value = line
					ina_pass1 = (_("Password") + ":", self.ina_pass)
					self.list.append(ina_pass1)
				elif line.startswith('alias '):
					line = line[6:]
					self.ina_alias.value = line
					ina_alias1 = (_("Alias") + ":", self.ina_alias)
					self.list.append(ina_alias1)
				elif line.startswith('update_period_sec '):
					line = line[18:]
					line = (int(line) / 60)
					self.ina_period.value = line
					ina_period1 = (_("Time Update in Minutes") + ":", self.ina_period)
					self.list.append(ina_period1)
				elif line.startswith('dyndns_system ') or line.startswith('#dyndns_system '):
					if not line.startswith('#'):
						self.ina_sysactive.value = True
						line = line[14:]
					else:
						self.ina_sysactive.value = False
						line = line[15:]
					ina_sysactive1 = (_("Set System") + ":", self.ina_sysactive)
					self.list.append(ina_sysactive1)
					self.ina_value = line
					ina_system1 = (_("System") + ":", self.ina_system)
					self.list.append(ina_system1)

			f.close()
		self['config'].list = self.list
		self['config'].l.setList(self.list)

	def KeyText(self):
		sel = self['config'].getCurrent()
		if sel:
			if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
				if self["config"].getCurrent()[1].help_window.instance != None:
					self["config"].getCurrent()[1].help_window.hide()
			self.vkvar = sel[0]
			if self.vkvar == _("Username") + ':' or self.vkvar == _("Password") + ':' or self.vkvar == _("Alias") + ':' or self.vkvar == _("System") + ':':
				from Screens.VirtualKeyBoard import VirtualKeyBoard
				self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title=self["config"].getCurrent()[0], text=self["config"].getCurrent()[1].value)

	def VirtualKeyBoardCallback(self, callback=None):
		if callback != None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def saveIna(self):
		if fileExists('/etc/inadyn.conf'):
			inme = open('/etc/inadyn.conf', 'r')
			out = open('/etc/inadyn.conf.tmp', 'w')
			for line in inme.readlines():
				line = line.replace('\n', '')
				if line.startswith('username '):
					line = ('username ' + self.ina_user.value.strip())
				elif line.startswith('password '):
					line = ('password ' + self.ina_pass.value.strip())
				elif line.startswith('alias '):
					line = ('alias ' + self.ina_alias.value.strip())
				elif line.startswith('update_period_sec '):
					strview = (self.ina_period.value * 60)
					strview = str(strview)
					line = ('update_period_sec ' + strview)
				elif line.startswith('dyndns_system ') or line.startswith('#dyndns_system '):
					if self.ina_sysactive.value:
						line = ('dyndns_system ' + self.ina_system.value.strip())
					else:
						line = ('#dyndns_system ' + self.ina_system.value.strip())
				out.write((line + '\n'))
			out.close()
			inme.close()
		else:
			self.session.open(MessageBox, _("Sorry Inadyn Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if fileExists('/etc/inadyn.conf.tmp'):
			rename('/etc/inadyn.conf.tmp', '/etc/inadyn.conf')
		self.myStop()

	def myStop(self):
		self.close()


class NetworkInadynLog(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Inadyn Log"))
		self['infotext'] = ScrollLabel('')
		self['actions'] = ActionMap(['WizardActions', 'DirectionActions', 'ColorActions'], {'ok': self.close,
		 'back': self.close,
		 'up': self['infotext'].pageUp,
		 'down': self['infotext'].pageDown})
		strview = ''
		if fileExists('/var/log/inadyn.log'):
			f = open('/var/log/inadyn.log', 'r')
			for line in f.readlines():
				strview += line
			f.close()
		self['infotext'].setText(strview)


config.networkushare = ConfigSubsection()
config.networkushare.mediafolders = NoSave(ConfigLocations(default=""))


class NetworkuShare(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("uShare Setup"))
		self.onChangedEntry = []
		self['autostart'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Active")))
		self['labdisabled'] = Label(_(_("Disabled")))
		self['status'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['username'] = Label(_("uShare Name") + ":")
		self['labuser'] = Label()
		self['iface'] = Label(_("Interface") + ":")
		self['labiface'] = Label()
		self['port'] = Label(_("uShare Port") + ":")
		self['labport'] = Label()
		self['telnetport'] = Label(_("Telnet Port") + ":")
		self['labtelnetport'] = Label()
		self['sharedir'] = Label(_("Share Folder's") + ":")
		self['labsharedir'] = Label()
		self['web'] = Label(_("Web Interface") + ":")
		self['webactive'] = Pixmap()
		self['webinactive'] = Pixmap()
		self['telnet'] = Label(_("Telnet Interface") + ":")
		self['telnetactive'] = Pixmap()
		self['telnetinactive'] = Pixmap()
		self['xbox'] = Label(_("XBox 360 support") + ":")
		self['xboxactive'] = Pixmap()
		self['xboxinactive'] = Pixmap()
		self['dlna'] = Label(_("DLNA support") + ":")
		self['dlnaactive'] = Pixmap()
		self['dlnainactive'] = Pixmap()

		self['key_red'] = Label(_("Remove Service"))
		self['key_green'] = Label(_("Start"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label(_("Show Log"))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions', 'SetupActions'], {'ok': self.setupushare, 'back': self.close, 'menu': self.setupushare, 'red': self.UninstallCheck, 'green': self.uShareStartStop, 'yellow': self.autostart, 'blue': self.ushareLog})
		self.Console = Console()
		self.service_name = 'ushare'
		self.onLayoutFinish.append(self.InstallCheck)

	def InstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if 'Collected errors' in str:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is in progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif not str:
			self.feedscheck = self.session.open(MessageBox, _('Please wait while feeds state is checked.'), MessageBox.TYPE_INFO, enable_input=False)
			self.feedscheck.setTitle(_('Checking Feeds'))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			self.updateService()

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		result = six.ensure_str(result)
		if 'bad address' in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ('wget returned 1' or 'wget returned 255' or '404 Not Found') in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _('Ready to install %s ?') % self.service_name, MessageBox.TYPE_YESNO)

	def InstallPackage(self, val):
		if val:
			self.doInstall(self.installComplete, self.service_name)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname, callback)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.feedscheck.close()
		self.updateService()

	def UninstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if str:
			self.session.openWithCallback(self.RemovePackage, MessageBox, _('Ready to remove %s ?') % self.service_name, MessageBox.TYPE_YESNO)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove', callback)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.close()

	def createSummary(self):
		return NetworkServicesSummary

	def uShareStartStop(self):
		if not self.my_ushare_run:
			self.Console.ePopen('/etc/init.d/ushare start >> /tmp/uShare.log', self.StartStopCallback)
		elif self.my_ushare_run:
			self.Console.ePopen('/etc/init.d/ushare stop >> /tmp/uShare.log', self.StartStopCallback)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def autostart(self):
		if fileExists('/etc/rc2.d/S20ushare'):
			self.Console.ePopen('update-rc.d -f ushare remove', self.StartStopCallback)
		else:
			self.Console.ePopen('update-rc.d -f ushare defaults', self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		ushare_process = str(p.named('ushare')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].hide()
		self['labdisabled'].hide()
		self.my_ushare_active = False
		self.my_ushare_run = False
		if not fileExists('/tmp/uShare.log'):
			f = open('/tmp/uShare.log', "w")
			f.write("")
			f.close()
		if fileExists('/etc/rc2.d/S20ushare'):
			self['labdisabled'].hide()
			self['labactive'].show()
			self.my_ushare_active = True
			autostartstatus_summary = self['autostart'].text + ' ' + self['labactive'].text
		else:
			self['labactive'].hide()
			self['labdisabled'].show()
			autostartstatus_summary = self['autostart'].text + ' ' + self['labdisabled'].text
		if ushare_process:
			self.my_ushare_run = True
		if self.my_ushare_run:
			self['labstop'].hide()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['status'].text + ' ' + self['labstop'].text
		else:
			self['labstop'].show()
			self['labrun'].hide()
			self['key_green'].setText(_("Start"))
			status_summary = self['status'].text + ' ' + self['labstop'].text

		if fileExists('/etc/ushare.conf'):
			f = open('/etc/ushare.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('USHARE_NAME='):
					line = line[12:]
					self['labuser'].setText(line)
				elif line.startswith('USHARE_IFACE='):
					line = line[13:]
					self['labiface'].setText(line)
				elif line.startswith('USHARE_PORT='):
					line = line[12:]
					self['labport'].setText(line)
				elif line.startswith('USHARE_TELNET_PORT='):
					line = line[19:]
					self['labtelnetport'].setText(line)
				elif line.startswith('USHARE_DIR='):
					line = line[11:]
					self.mediafolders = line
					self['labsharedir'].setText(line)
				elif line.startswith('ENABLE_WEB='):
					if line[11:] == 'no':
						self['webactive'].hide()
						self['webinactive'].show()
					else:
						self['webactive'].show()
						self['webinactive'].hide()
				elif line.startswith('ENABLE_TELNET='):
					if line[14:] == 'no':
						self['telnetactive'].hide()
						self['telnetinactive'].show()
					else:
						self['telnetactive'].show()
						self['telnetinactive'].hide()
				elif line.startswith('ENABLE_XBOX='):
					if line[12:] == 'no':
						self['xboxactive'].hide()
						self['xboxinactive'].show()
					else:
						self['xboxactive'].show()
						self['xboxinactive'].hide()
				elif line.startswith('ENABLE_DLNA='):
					if line[12:] == 'no':
						self['dlnaactive'].hide()
						self['dlnainactive'].show()
					else:
						self['dlnaactive'].show()
						self['dlnainactive'].hide()
			f.close()
		title = _("uShare Setup")

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

	def setupushare(self):
		self.session.openWithCallback(self.updateService, NetworkuShareSetup)

	def ushareLog(self):
		self.session.open(NetworkuShareLog)


class NetworkuShareSetup(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("uShare Setup"))
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.selectionChanged)
		Screen.setTitle(self, _("uShare Setup"))
		self['key_red'] = Label(_("Save"))
		self['key_green'] = Label(_("Shares"))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions', 'VirtualKeyboardActions'], {'red': self.saveuShare, 'green': self.selectfolders, 'back': self.close, 'showVirtualKeyboard': self.KeyText})
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.updateList()
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["config"].getCurrent()
		if item:
			name = str(item[0])
			desc = str(item[1].value)
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def updateList(self, ret=None):
		self.list = []
		self.ushare_user = NoSave(ConfigText(default=getBoxType(), fixed_size=False))
		self.ushare_iface = NoSave(ConfigText(fixed_size=False))
		self.ushare_port = NoSave(ConfigNumber())
		self.ushare_telnetport = NoSave(ConfigNumber())
		self.ushare_web = NoSave(ConfigYesNo(default='True'))
		self.ushare_telnet = NoSave(ConfigYesNo(default='True'))
		self.ushare_xbox = NoSave(ConfigYesNo(default='True'))
		self.ushare_ps3 = NoSave(ConfigYesNo(default='True'))
		self.ushare_system = NoSave(ConfigSelection(default="dyndns@dyndns.org", choices=[("dyndns@dyndns.org", "dyndns@dyndns.org"), ("statdns@dyndns.org", "statdns@dyndns.org"), ("custom@dyndns.org", "custom@dyndns.org")]))

		if fileExists('/etc/ushare.conf'):
			f = open('/etc/ushare.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('USHARE_NAME='):
					line = line[12:]
					self.ushare_user.value = line
					ushare_user1 = (_("uShare Name") + ":", self.ushare_user)
					self.list.append(ushare_user1)
				elif line.startswith('USHARE_IFACE='):
					line = line[13:]
					self.ushare_iface.value = line
					ushare_iface1 = (_("Interface") + ":", self.ushare_iface)
					self.list.append(ushare_iface1)
				elif line.startswith('USHARE_PORT='):
					line = line[12:]
					self.ushare_port.value = line
					ushare_port1 = (_("uShare Port") + ":", self.ushare_port)
					self.list.append(ushare_port1)
				elif line.startswith('USHARE_TELNET_PORT='):
					line = line[19:]
					self.ushare_telnetport.value = line
					ushare_telnetport1 = (_("Telnet Port") + ":", self.ushare_telnetport)
					self.list.append(ushare_telnetport1)
				elif line.startswith('ENABLE_WEB='):
					if line[11:] == 'no':
						self.ushare_web.value = False
					else:
						self.ushare_web.value = True
					ushare_web1 = (_("Web Interface") + ":", self.ushare_web)
					self.list.append(ushare_web1)
				elif line.startswith('ENABLE_TELNET='):
					if line[14:] == 'no':
						self.ushare_telnet.value = False
					else:
						self.ushare_telnet.value = True
					ushare_telnet1 = (_("Telnet Interface") + ":", self.ushare_telnet)
					self.list.append(ushare_telnet1)
				elif line.startswith('ENABLE_XBOX='):
					if line[12:] == 'no':
						self.ushare_xbox.value = False
					else:
						self.ushare_xbox.value = True
					ushare_xbox1 = (_("XBox 360 support") + ":", self.ushare_xbox)
					self.list.append(ushare_xbox1)
				elif line.startswith('ENABLE_DLNA='):
					if line[12:] == 'no':
						self.ushare_ps3.value = False
					else:
						self.ushare_ps3.value = True
					ushare_ps31 = (_("DLNA support") + ":", self.ushare_ps3)
					self.list.append(ushare_ps31)
			f.close()
		self['config'].list = self.list
		self['config'].l.setList(self.list)

	def KeyText(self):
		sel = self['config'].getCurrent()
		if sel:
			if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
				if self["config"].getCurrent()[1].help_window.instance != None:
					self["config"].getCurrent()[1].help_window.hide()
			self.vkvar = sel[0]
			if self.vkvar == _("uShare Name") + ":" or self.vkvar == _("Share Folder's") + ":":
				from Screens.VirtualKeyBoard import VirtualKeyBoard
				self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title=self["config"].getCurrent()[0], text=self["config"].getCurrent()[1].value)

	def VirtualKeyBoardCallback(self, callback=None):
		if callback != None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def saveuShare(self):
		if fileExists('/etc/ushare.conf'):
			inme = open('/etc/ushare.conf', 'r')
			out = open('/etc/ushare.conf.tmp', 'w')
			for line in inme.readlines():
				line = line.replace('\n', '')
				if line.startswith('USHARE_NAME='):
					line = ('USHARE_NAME=' + self.ushare_user.value.strip())
				elif line.startswith('USHARE_IFACE='):
					line = ('USHARE_IFACE=' + self.ushare_iface.value.strip())
				elif line.startswith('USHARE_PORT='):
					line = ('USHARE_PORT=' + str(self.ushare_port.value))
				elif line.startswith('USHARE_TELNET_PORT='):
					line = ('USHARE_TELNET_PORT=' + str(self.ushare_telnetport.value))
				elif line.startswith('USHARE_DIR='):
					line = ('USHARE_DIR=' + ', '.join(config.networkushare.mediafolders.value))
				elif line.startswith('ENABLE_WEB='):
					if not self.ushare_web.value:
						line = 'ENABLE_WEB=no'
					else:
						line = 'ENABLE_WEB=yes'
				elif line.startswith('ENABLE_TELNET='):
					if not self.ushare_telnet.value:
						line = 'ENABLE_TELNET=no'
					else:
						line = 'ENABLE_TELNET=yes'
				elif line.startswith('ENABLE_XBOX='):
					if not self.ushare_xbox.value:
						line = 'ENABLE_XBOX=no'
					else:
						line = 'ENABLE_XBOX=yes'
				elif line.startswith('ENABLE_DLNA='):
					if not self.ushare_ps3.value:
						line = 'ENABLE_DLNA=no'
					else:
						line = 'ENABLE_DLNA=yes'
				out.write((line + '\n'))
			out.close()
			inme.close()
		else:
			open('/tmp/uShare.log', "a").write(_("Sorry uShare Config is Missing") + '\n')
			self.session.open(MessageBox, _("Sorry uShare Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if fileExists('/etc/ushare.conf.tmp'):
			rename('/etc/ushare.conf.tmp', '/etc/ushare.conf')
		self.myStop()

	def myStop(self):
		self.close()

	def selectfolders(self):
		try:
			self["config"].getCurrent()[1].help_window.hide()
		except:
			pass
		self.session.openWithCallback(self.updateList, uShareSelection)


class uShareSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Select folders"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText()

		if fileExists('/etc/ushare.conf'):
			f = open('/etc/ushare.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('USHARE_DIR='):
					line = line[11:]
					self.mediafolders = line
		self.selectedFiles = [str(n) for n in self.mediafolders.split(', ')]
		defaultDir = '/media/'
		self.filelist = MultiFileSelectList(self.selectedFiles, defaultDir, showFiles=False)
		self["checkList"] = self.filelist

		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions", "ShortcutActions"],
		{
			"cancel": self.exit,
			"red": self.exit,
			"yellow": self.changeSelectionState,
			"green": self.saveSelection,
			"ok": self.okClicked,
			"left": self.left,
			"right": self.right,
			"down": self.down,
			"up": self.up
		}, -1)
		if not self.selectionChanged in self["checkList"].onSelectionChanged:
			self["checkList"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		idx = 0
		self["checkList"].moveToIndex(idx)
		self.selectionChanged()

	def selectionChanged(self):
		current = self["checkList"].getCurrent()[0]
		try:
			if current[2] == True:
				self["key_yellow"].setText(_("Deselect"))
			else:
				self["key_yellow"].setText(_("Select"))
		except:
			pass

	def up(self):
		self["checkList"].up()

	def down(self):
		self["checkList"].down()

	def left(self):
		self["checkList"].pageUp()

	def right(self):
		self["checkList"].pageDown()

	def changeSelectionState(self):
		self["checkList"].changeSelectionState()
		self.selectedFiles = self["checkList"].getSelectedList()

	def saveSelection(self):
		self.selectedFiles = self["checkList"].getSelectedList()
		config.networkushare.mediafolders.value = self.selectedFiles
		self.close(None)

	def exit(self):
		self.close(None)

	def okClicked(self):
		if self.filelist.canDescent():
			self.filelist.descent()


class NetworkuShareLog(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "NetworkInadynLog"
		Screen.setTitle(self, _("uShare Log"))
		self['infotext'] = ScrollLabel('')
		self.Console = Console()
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'up': self['infotext'].pageUp, 'down': self['infotext'].pageDown})
		strview = ''
		self.Console.ePopen('tail /tmp/uShare.log > /tmp/tmp.log')
		time.sleep(1)
		if fileExists('/tmp/tmp.log'):
			f = open('/tmp/tmp.log', 'r')
			for line in f.readlines():
				strview += line
			f.close()
			remove('/tmp/tmp.log')
		self['infotext'].setText(strview)


config.networkminidlna = ConfigSubsection()
config.networkminidlna.mediafolders = NoSave(ConfigLocations(default=""))


class NetworkMiniDLNA(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("MiniDLNA Setup"))
		self.onChangedEntry = []
		self['autostart'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Active")))
		self['labdisabled'] = Label(_(_("Disabled")))
		self['status'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['username'] = Label(_("Name") + ":")
		self['labuser'] = Label()
		self['iface'] = Label(_("Interface") + ":")
		self['labiface'] = Label()
		self['port'] = Label(_("Port") + ":")
		self['labport'] = Label()
		self['serialno'] = Label(_("Serial No") + ":")
		self['labserialno'] = Label()
		self['sharedir'] = Label(_("Share Folder's") + ":")
		self['labsharedir'] = Label()
		self['inotify'] = Label(_("Inotify Monitoring") + ":")
		self['inotifyactive'] = Pixmap()
		self['inotifyinactive'] = Pixmap()
		self['tivo'] = Label(_("TiVo support") + ":")
		self['tivoactive'] = Pixmap()
		self['tivoinactive'] = Pixmap()
		self['dlna'] = Label(_("Strict DLNA") + ":")
		self['dlnaactive'] = Pixmap()
		self['dlnainactive'] = Pixmap()

		self['key_red'] = Label(_("Remove Service"))
		self['key_green'] = Label(_("Start"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label(_("Show Log"))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions', 'SetupActions'], {'ok': self.setupminidlna, 'back': self.close, 'menu': self.setupminidlna, 'red': self.UninstallCheck, 'green': self.MiniDLNAStartStop, 'yellow': self.autostart, 'blue': self.minidlnaLog})
		self.Console = Console()
		self.service_name = 'minidlna'
		self.onLayoutFinish.append(self.InstallCheck)

	def InstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if 'Collected errors' in str:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is in progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif not str:
			self.feedscheck = self.session.open(MessageBox, _('Please wait while feeds state is checked.'), MessageBox.TYPE_INFO, enable_input=False)
			self.feedscheck.setTitle(_('Checking Feeds'))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			self.updateService()

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		result = six.ensure_str(result)
		if 'bad address' in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ('wget returned 1' or 'wget returned 255' or '404 Not Found') in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _('Ready to install %s ?') % self.service_name, MessageBox.TYPE_YESNO)

	def InstallPackage(self, val):
		if val:
			self.doInstall(self.installComplete, self.service_name)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname, callback)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.feedscheck.close()
		self.updateService()

	def UninstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if str:
			self.session.openWithCallback(self.RemovePackage, MessageBox, _('Ready to remove %s ?') % self.service_name, MessageBox.TYPE_YESNO)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove', callback)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.close()

	def createSummary(self):
		return NetworkServicesSummary

	def MiniDLNAStartStop(self):
		if not self.my_minidlna_run:
			self.Console.ePopen('/etc/init.d/minidlna start', self.StartStopCallback)
		elif self.my_minidlna_run:
			self.Console.ePopen('/etc/init.d/minidlna stop', self.StartStopCallback)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def autostart(self):
		if fileExists('/etc/rc2.d/S20minidlna'):
			self.Console.ePopen('update-rc.d -f minidlna remove', self.StartStopCallback)
		else:
			self.Console.ePopen('update-rc.d -f minidlna defaults', self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		minidlna_process = str(p.named('minidlnad')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].hide()
		self['labdisabled'].hide()
		self.my_minidlna_active = False
		self.my_minidlna_run = False
		if fileExists('/etc/rc2.d/S20minidlna'):
			self['labdisabled'].hide()
			self['labactive'].show()
			self.my_minidlna_active = True
			autostartstatus_summary = self['autostart'].text + ' ' + self['labactive'].text
		else:
			self['labactive'].hide()
			self['labdisabled'].show()
			autostartstatus_summary = self['autostart'].text + ' ' + self['labdisabled'].text
		if minidlna_process:
			self.my_minidlna_run = True
		if self.my_minidlna_run:
			self['labstop'].hide()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['status'].text + ' ' + self['labstop'].text
		else:
			self['labstop'].show()
			self['labrun'].hide()
			self['key_green'].setText(_("Start"))
			status_summary = self['status'].text + ' ' + self['labstop'].text

		if fileExists('/etc/minidlna.conf'):
			f = open('/etc/minidlna.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('friendly_name='):
					line = line[14:]
					self['labuser'].setText(line)
				elif line.startswith('network_interface='):
					line = line[18:]
					self['labiface'].setText(line)
				elif line.startswith('port='):
					line = line[5:]
					self['labport'].setText(line)
				elif line.startswith('serial='):
					line = line[7:]
					self['labserialno'].setText(line)
				elif line.startswith('media_dir='):
					line = line[10:]
					self.mediafolders = line
					self['labsharedir'].setText(line)
				elif line.startswith('inotify='):
					if line[8:] == 'no':
						self['inotifyactive'].hide()
						self['inotifyinactive'].show()
					else:
						self['inotifyactive'].show()
						self['inotifyinactive'].hide()
				elif line.startswith('enable_tivo='):
					if line[12:] == 'no':
						self['tivoactive'].hide()
						self['tivoinactive'].show()
					else:
						self['tivoactive'].show()
						self['tivoinactive'].hide()
				elif line.startswith('strict_dlna='):
					if line[12:] == 'no':
						self['dlnaactive'].hide()
						self['dlnainactive'].show()
					else:
						self['dlnaactive'].show()
						self['dlnainactive'].hide()
			f.close()
		title = _("MiniDLNA Setup")

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

	def setupminidlna(self):
		self.session.openWithCallback(self.updateService, NetworkMiniDLNASetup)

	def minidlnaLog(self):
		self.session.open(NetworkMiniDLNALog)


class NetworkMiniDLNASetup(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("MiniDLNA Setup"))
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.selectionChanged)
		Screen.setTitle(self, _("MiniDLNA Setup"))
		self.skinName = "NetworkuShareSetup"
		self['key_red'] = Label(_("Save"))
		self['key_green'] = Label(_("Shares"))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions', 'VirtualKeyboardActions'], {'red': self.saveMinidlna, 'green': self.selectfolders, 'back': self.close, 'showVirtualKeyboard': self.KeyText})
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.updateList()
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["config"].getCurrent()
		if item:
			name = str(item[0])
			desc = str(item[1].value)
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def updateList(self, ret=None):
		self.list = []
		self.minidlna_name = NoSave(ConfigText(default=getBoxType(), fixed_size=False))
		self.minidlna_iface = NoSave(ConfigText(fixed_size=False))
		self.minidlna_port = NoSave(ConfigNumber())
		self.minidlna_serialno = NoSave(ConfigNumber())
		self.minidlna_web = NoSave(ConfigYesNo(default='True'))
		self.minidlna_inotify = NoSave(ConfigYesNo(default='True'))
		self.minidlna_tivo = NoSave(ConfigYesNo(default='True'))
		self.minidlna_strictdlna = NoSave(ConfigYesNo(default='True'))

		if fileExists('/etc/minidlna.conf'):
			f = open('/etc/minidlna.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('friendly_name='):
					line = line[14:]
					self.minidlna_name.value = line
					minidlna_name1 = (_("Name") + ":", self.minidlna_name)
					self.list.append(minidlna_name1)
				elif line.startswith('network_interface='):
					line = line[18:]
					self.minidlna_iface.value = line
					minidlna_iface1 = (_("Interface") + ":", self.minidlna_iface)
					self.list.append(minidlna_iface1)
				elif line.startswith('port='):
					line = line[5:]
					self.minidlna_port.value = line
					minidlna_port1 = (_("Port") + ":", self.minidlna_port)
					self.list.append(minidlna_port1)
				elif line.startswith('serial='):
					line = line[7:]
					self.minidlna_serialno.value = line
					minidlna_serialno1 = (_("Serial No") + ":", self.minidlna_serialno)
					self.list.append(minidlna_serialno1)
				elif line.startswith('inotify='):
					if line[8:] == 'no':
						self.minidlna_inotify.value = False
					else:
						self.minidlna_inotify.value = True
					minidlna_inotify1 = (_("Inotify Monitoring") + ":", self.minidlna_inotify)
					self.list.append(minidlna_inotify1)
				elif line.startswith('enable_tivo='):
					if line[12:] == 'no':
						self.minidlna_tivo.value = False
					else:
						self.minidlna_tivo.value = True
					minidlna_tivo1 = (_("TiVo support") + ":", self.minidlna_tivo)
					self.list.append(minidlna_tivo1)
				elif line.startswith('strict_dlna='):
					if line[12:] == 'no':
						self.minidlna_strictdlna.value = False
					else:
						self.minidlna_strictdlna.value = True
					minidlna_strictdlna1 = (_("Strict DLNA") + ":", self.minidlna_strictdlna)
					self.list.append(minidlna_strictdlna1)
			f.close()
		self['config'].list = self.list
		self['config'].l.setList(self.list)

	def KeyText(self):
		sel = self['config'].getCurrent()
		if sel:
			if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
				if self["config"].getCurrent()[1].help_window.instance != None:
					self["config"].getCurrent()[1].help_window.hide()
			self.vkvar = sel[0]
			if self.vkvar == _("Name") + ":" or self.vkvar == _("Share Folder's") + ":":
				from Screens.VirtualKeyBoard import VirtualKeyBoard
				self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title=self["config"].getCurrent()[0], text=self["config"].getCurrent()[1].value)

	def VirtualKeyBoardCallback(self, callback=None):
		if callback != None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def saveMinidlna(self):
		if fileExists('/etc/minidlna.conf'):
			inme = open('/etc/minidlna.conf', 'r')
			out = open('/etc/minidlna.conf.tmp', 'w')
			for line in inme.readlines():
				line = line.replace('\n', '')
				if line.startswith('friendly_name='):
					line = ('friendly_name=' + self.minidlna_name.value.strip())
				elif line.startswith('network_interface='):
					line = ('network_interface=' + self.minidlna_iface.value.strip())
				elif line.startswith('port='):
					line = ('port=' + str(self.minidlna_port.value))
				elif line.startswith('serial='):
					line = ('serial=' + str(self.minidlna_serialno.value))
				elif line.startswith('media_dir='):
					line = ('media_dir=' + ', '.join(config.networkminidlna.mediafolders.value))
				elif line.startswith('inotify='):
					if not self.minidlna_inotify.value:
						line = 'inotify=no'
					else:
						line = 'inotify=yes'
				elif line.startswith('enable_tivo='):
					if not self.minidlna_tivo.value:
						line = 'enable_tivo=no'
					else:
						line = 'enable_tivo=yes'
				elif line.startswith('strict_dlna='):
					if not self.minidlna_strictdlna.value:
						line = 'strict_dlna=no'
					else:
						line = 'strict_dlna=yes'
				out.write((line + '\n'))
			out.close()
			inme.close()
		else:
			self.session.open(MessageBox, _("Sorry MiniDLNA Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if fileExists('/etc/minidlna.conf.tmp'):
			rename('/etc/minidlna.conf.tmp', '/etc/minidlna.conf')
		self.myStop()

	def myStop(self):
		self.close()

	def selectfolders(self):
		try:
			self["config"].getCurrent()[1].help_window.hide()
		except:
			pass
		self.session.openWithCallback(self.updateList, MiniDLNASelection)


class MiniDLNASelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Select folders"))
		self.skinName = "uShareSelection"
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText()

		if fileExists('/etc/minidlna.conf'):
			f = open('/etc/minidlna.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('media_dir='):
					line = line[11:]
					self.mediafolders = line
		self.selectedFiles = [str(n) for n in self.mediafolders.split(', ')]
		defaultDir = '/media/'
		self.filelist = MultiFileSelectList(self.selectedFiles, defaultDir, showFiles=False)
		self["checkList"] = self.filelist

		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions", "ShortcutActions"],
		{
			"cancel": self.exit,
			"red": self.exit,
			"yellow": self.changeSelectionState,
			"green": self.saveSelection,
			"ok": self.okClicked,
			"left": self.left,
			"right": self.right,
			"down": self.down,
			"up": self.up
		}, -1)
		if not self.selectionChanged in self["checkList"].onSelectionChanged:
			self["checkList"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		idx = 0
		self["checkList"].moveToIndex(idx)
		self.selectionChanged()

	def selectionChanged(self):
		current = self["checkList"].getCurrent()[0]
		try:
			if current[2] == True:
				self["key_yellow"].setText(_("Deselect"))
			else:
				self["key_yellow"].setText(_("Select"))
		except:
			pass

	def up(self):
		self["checkList"].up()

	def down(self):
		self["checkList"].down()

	def left(self):
		self["checkList"].pageUp()

	def right(self):
		self["checkList"].pageDown()

	def changeSelectionState(self):
		self["checkList"].changeSelectionState()
		self.selectedFiles = self["checkList"].getSelectedList()

	def saveSelection(self):
		self.selectedFiles = self["checkList"].getSelectedList()
		config.networkminidlna.mediafolders.value = self.selectedFiles
		self.close(None)

	def exit(self):
		self.close(None)

	def okClicked(self):
		if self.filelist.canDescent():
			self.filelist.descent()


class NetworkMiniDLNALog(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "NetworkInadynLog"
		Screen.setTitle(self, _("MiniDLNA Log"))
		self['infotext'] = ScrollLabel('')
		self.Console = Console()
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'up': self['infotext'].pageUp, 'down': self['infotext'].pageDown})
		strview = ''
		self.Console.ePopen('tail /var/volatile/log/minidlna.log > /tmp/tmp.log')
		time.sleep(1)
		if fileExists('/tmp/tmp.log'):
			f = open('/tmp/tmp.log', 'r')
			for line in f.readlines():
				strview += line
			f.close()
			remove('/tmp/tmp.log')
		self['infotext'].setText(strview)


class NetworkSATPI(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("SATPI Setup"))
		self.skinName = "NetworkSATPI"
		self.onChangedEntry = []
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_red'] = Label(_("Remove Service"))
		self['key_green'] = Label(_("Start"))
		self['key_yellow'] = Label(_("Autostart"))
		self['status_summary'] = StaticText()
		self['autostartstatus_summary'] = StaticText()
		self.Console = Console()
		self.my_satpi_active = False
		self.my_satpi_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.UninstallCheck, 'green': self.SATPIStartStop, 'yellow': self.activateSATPI})
		self.service_name = 'satpi'
		self.checkSATPIService()

	def checkSATPIService(self):
		print('INSTALL CHECK STARTED', self.service_name)
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		print('INSTALL CHECK FINISHED', str)
		if not str:
			self.feedscheck = self.session.open(MessageBox, _('Please wait while feeds state is checked.'), MessageBox.TYPE_INFO, enable_input=False)
			self.feedscheck.setTitle(_('Checking Feeds'))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			print('INSTALL ALREADY INSTALLED')
			self.updateService()

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		result = six.ensure_str(result)
		if (float(getEnigmaVersionString()) < 3.0 and result.find('mipsel/Packages.gz, wget returned 1') != -1) or (float(getEnigmaVersionString()) >= 3.0 and result.find('mips32el/Packages.gz, wget returned 1') != -1):
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif result.find('bad address') != -1:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _('Ready to install %s ?') % self.service_name, MessageBox.TYPE_YESNO)

	def InstallPackage(self, val):
		if val:
			self.doInstall(self.installComplete, self.service_name)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname, callback)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.feedscheck.close()
		self.updateService()

	def UninstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		str = six.ensure_str(str)
		if str:
			self.session.openWithCallback(self.RemovePackage, MessageBox, _('Ready to remove %s ?') % self.service_name, MessageBox.TYPE_YESNO)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove', callback)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.updateService()

	def createSummary(self):
		return NetworkServicesSummary

	def SATPIStartStop(self):
		if not self.my_satpi_run:
			self.Console.ePopen('/etc/init.d/satpi start')
			time.sleep(3)
			self.updateService()
		elif self.my_satpi_run:
			self.Console.ePopen('/etc/init.d/satpi stop')
			time.sleep(3)
			self.updateService()

	def activateSATPI(self):
		if fileExists('/etc/rc2.d/S80satpi'):
			self.Console.ePopen('update-rc.d -f satpi remove')
		else:
			self.Console.ePopen('update-rc.d -f satpi defaults 80')
		time.sleep(3)
		self.updateService()

	def updateService(self, result=None, retval=None, extra_args=None):
		import process
		p = process.ProcessList()
		satpi_process = str(p.named('satpi')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_satpi_active = False
		self.my_satpi_run = False
		if fileExists('/etc/rc2.d/S80satpi'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_satpi_active = True
		if satpi_process:
			self.my_satpi_run = True
		if self.my_satpi_run:
			self['labstop'].hide()
			self['labactive'].show()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['lab2'].text + ' ' + self['labrun'].text
		else:
			self['labrun'].hide()
			self['labstop'].show()
			self['labactive'].show()
			self['key_green'].setText(_("Start"))
			status_summary = self['lab2'].text + ' ' + self['labstop'].text
		title = _("SATPI Setup")
		autostartstatus_summary = self['lab1'].text + ' ' + self['labactive'].text

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


class NetworkServicesSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["title"] = StaticText("")
		self["status_summary"] = StaticText("")
		self["autostartstatus_summary"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.updateService()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, title, status_summary, autostartstatus_summary):
		self["title"].text = title
		self["status_summary"].text = status_summary
		self["autostartstatus_summary"].text = autostartstatus_summary
