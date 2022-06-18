# coding:utf-8
import sys
import sqlite3 as sl
import RPi.GPIO as GPIO
import signal
from mfrc522 import MFRC522
import datetime
import passwordFrame
from bmob.bmob import *
import time

reload(sys)
sys.setdefaultencoding('utf8')
import wx
from dialog.SucessDialog import SucessDialog
from dialog.FailDialog import FailDialog

ID_CALC = 300


class BorrowBooksFrame(wx.Frame):
    def __init__(self, parent=None, id=-1, UpdateUI=None):
        wx.Frame.__init__(self, parent, id, title=u'图书管理系统', size=(400, 400), pos=(500, 200))

        self.UpdateUI = UpdateUI
        self.InitUI()

    def InitUI(self):
        self.panel = wx.Panel(self, -1)
        global ID_CALC

        vbox = wx.BoxSizer(wx.VERTICAL)

        con = sl.connect("user.db")
        data = con.execute("SELECT * FROM USER")
        for row in data:
            print(row[0] + row[1])
            self.uid = row[0]
            self.uname = row[1]
        user_list = [u'姓名:' + self.uname, u'卡号:' + self.uid]
        user_message = []
        for i, button in enumerate(user_list):
            user_message.append(wx.StaticText(self.panel, -1, button, pos=(30, 30), style=wx.ALIGN_CENTER))

        gs = wx.GridSizer(1, 2, 20, 50)
        gs.AddMany(user_message)

        vbox.Add(gs, 0, wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL, 20)

        book_list = [u'书名:', u'书号:']
        book_message = []

        self.book_name = wx.StaticText(self.panel, -1, book_list[0], pos=(30, 30), style=wx.ALIGN_CENTER)
        book_message.append(self.book_name)
        self.book_id = wx.StaticText(self.panel, -1, book_list[1], pos=(30, 30), style=wx.ALIGN_CENTER)
        book_message.append(self.book_id)


        gs = wx.GridSizer(1, 2, 20, 50)
        gs.AddMany(book_message)

        vbox.Add(gs, 0, wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL, 20)

        button_list = [u'借阅', u'退出']
        buttons = []
        for i, button in enumerate(button_list):
            buttons.append((wx.Button(self.panel, ID_CALC, label="{}".format(button), size=(50, 40)), 0, wx.EXPAND))
            self.Bind(wx.EVT_BUTTON, self.OnCalcClick, id=ID_CALC)
            ID_CALC = ID_CALC + 1

        gs = wx.GridSizer(1, 2, 20, 50)
        gs.AddMany(buttons)

        vbox.Add(gs, 0, wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL, 20)

        self.timer = wx.PyTimer(self.Notify)
        self.timer.Start(3000, wx.TIMER_CONTINUOUS)
        self.Notify()

        self.panel.SetSizer(vbox)

    def OnCalcClick(self, event):
        if event.GetEventObject().GetLabel() == u'退出':
            con = sl.connect("user.db")
            con.execute("DELETE FROM USER")
            con = sl.connect("user.db")

            data = con.execute("SELECT * FROM USER")
            for row in data:
                print(row[0] + row[1])
            self.UpdateUI(0)
            self.ClearUI()
        elif event.GetEventObject().GetLabel() == u'借阅':
            b = Bmob("57f90426c26325c00142548619a79b64", "f70e16d5cef5f241737cb6cd311ac762")
            account = b.find(
                "Book",
                BmobQuerier().
                    addWhereEqualTo("id", self.bid)
            )
            data2 = json.loads(account.stringData)
            d1 = data2["results"]
            for i, d2 in enumerate(d1):
                self.status = d2["status"]

            if self.status:
                print b.insert(
                    'BorrowBooks',
                    BmobUpdater.increment(
                        "count",
                        2,
                        {
                            "userId": str(self.uid),
                            "bookId": str(self.bid),
                            "time": str(datetime.date.today()),
                            "status": False
                        }
                    )
                ).jsonData

                print b.update(
                    "Book",
                    str(self.book_object),
                    BmobUpdater.increment(
                        "count",  # 原子计数key
                        2,  # 原子计数值
                        {  # 额外信息
                            "status": False
                        }
                    )
                ).jsonData
                dlg = SucessDialog(None, -1)
                dlg.ShowModal()
                dlg.Destroy()
            else:
                dlg = FailDialog(None, -1)
                dlg.ShowModal()
                dlg.Destroy()

    def Notify(self):
        id = self.ReadUserOrBook()
        if id is not None:
            self.UpdateMessage(id)

    def UpdateMessage(self, id):

        b = Bmob("57f90426c26325c00142548619a79b64", "f70e16d5cef5f241737cb6cd311ac762")
        account = b.find(
            "Book",
            BmobQuerier().
                addWhereEqualTo("id", id)
        )
        print account.err
        if account.err is None:
            data2 = json.loads(account.stringData)
            d1 = data2["results"]
            for i, d2 in enumerate(d1):
                self.bid = d2["id"]
                self.bname = d2["name"]
                self.book_name.SetLabel("书名:" + d2["name"])
                self.book_id.SetLabel("书号:" + d2["id"])
                self.book_object = d2["objectId"]

    def ReadUserOrBook(self):
        continue_reading = True

        def end_read(signal, frame):
            global continue_reading
            print
            "Ctrl+C captured, ending read."
            continue_reading = False
            GPIO.cleanup()

        signal.signal(signal.SIGINT, end_read)

        MIFAREReader = MFRC522()

        (status, TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

        if status == MIFAREReader.MI_OK:
            print "Card detected"

            (status, uid) = MIFAREReader.MFRC522_Anticoll()

            if status == MIFAREReader.MI_OK:

                print self.Comfort(uid[0]) + self.Comfort(uid[1]) + self.Comfort(uid[2]) + self.Comfort(uid[3])

                key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

                MIFAREReader.MFRC522_SelectTag(uid)

                status = MIFAREReader.MFRC522_Auth(MIFAREReader.PICC_AUTHENT1A, 8, key, uid)

                if status == MIFAREReader.MI_OK:
                    MIFAREReader.MFRC522_Read(8)
                    MIFAREReader.MFRC522_StopCrypto1()
                    return self.Comfort(uid[0]) + self.Comfort(uid[1]) + self.Comfort(uid[2]) + self.Comfort(uid[3])
                else:
                    print "Authentication error"

        print None
        return None

    def Comfort(self, id):
        if id >= 100:
            return str(id)
        elif id >= 10:
            return "0" + str(id)
        elif id >= 1:
            return "00" + str(id)
        else:
            return "000"

    def ClearUI(self):
        self.book_name.SetLabel("书名:")
        self.book_id.SetLabel("书号:")