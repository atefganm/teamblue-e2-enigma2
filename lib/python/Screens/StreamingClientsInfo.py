from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Converter.ClientsStreaming import ClientsStreaming
import skin
from enigma import eStreamServer, getDesktop
from Components.Sources.StaticText import StaticText

def getDesktopSize():
	s = getDesktop(0).size()
	return (s.width(), s.height())

def isHD():
	desktopSize = getDesktopSize()
	return desktopSize[0] == 1280


class StreamingClientsInfo(Screen):
	if isHD():
		skin = '''
			<screen name="StreamingClientsInfo" position="center,center" size="540,490" title="Streaming clients info">
				<widget name="menu" font="Regular;20" position="10,60" size="530,320" zPosition="1" />
				<widget name="info" position="10,60" size="530,22" font="Regular;20" halign="center" transparent="1" zPosition="2"/>
				<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on"/>
				<ePixmap pixmap="buttons/green.png" position="135,0" size="140,40" alphatest="on"/>
				<ePixmap pixmap="buttons/yellow.png" position="270,0" size="140,40" alphatest="on"/>
				<ePixmap pixmap="buttons/blue.png" position="405,0" size="140,40" alphatest="on"/>
				<widget name="key_red" position="0,0" zPosition="1" size="135,40" font="Regular;18" halign="center" valign="center" backgroundColor="#9f1313" transparent="1"/>
				<widget name="key_green" position="135,0" zPosition="1" size="135,40" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1"/>
				<widget name="key_yellow" position="270,0" zPosition="1" size="135,40" font="Regular;18" halign="center" valign="center" backgroundColor="#18188b" transparent="1"/>
			</screen>
		'''
	else:
		skin = '''
			<screen name="StreamingClientsInfo" position="center,center" size="850,900" title="Streaming clients info">
				<widget name="menu" font="Regular;28" itemHeight="40" position="10,135" size="830,756" zPosition="1" />
				<widget name="info" position="10,70" size="838,50" font="Regular;28" halign="center" transparent="1" zPosition="2"/>
				<ePixmap pixmap="buttons/red.png" position="0,0" size="200,50" alphatest="on"/>
				<ePixmap pixmap="buttons/green.png" position="210,0" size="200,50" alphatest="on"/>
				<ePixmap pixmap="buttons/yellow.png" position="425,0" size="200,50" alphatest="on"/>
				<ePixmap pixmap="buttons/blue.png" position="650,0" size="200,50" alphatest="on"/>
				<widget name="key_red" position="0,0" zPosition="1" size="200,50" font="Regular;28" halign="center" valign="center" backgroundColor="#9f1313" transparent="1"/>
				<widget name="key_green" position="210,0" zPosition="1" size="200,50" font="Regular;28" halign="center" valign="center" backgroundColor="#1f771f" transparent="1"/>
				<widget name="key_yellow" position="425,0" zPosition="1" size="200,50" font="Regular;28" halign="center" valign="center" backgroundColor="#18188b" transparent="1"/>
			</screen>
		'''

		def __init__(self, session):
			Screen.__init__(self, session)
			self.setTitle(_("Streaming clients info"))
			if ClientsStreaming("NUMBER").getText() == "0":
				self["total"] = StaticText(_("No streaming Channel from this STB at this moment"))
				text = ""
			else:
				self["total"] = StaticText(_("Total Clients streaming: ") + ClientsStreaming("NUMBER").getText())
				text = ClientsStreaming("EXTRA_INFO").getText()

			self["liste"] = StaticText(text)
			self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close
			})
