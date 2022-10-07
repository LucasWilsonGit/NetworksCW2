import time, socket, select, re, threading
from hashlib import sha256

class Message:
    """Message class, wraps behaviours serializing data to protocol packet format"""
    def __init__(self, FromStr=None, Body=None, ToStr = None, SubjectStr=None, TopicStr=None, Time=None):
        self.ID = ""
        if Time:
            self.Time = Time
        else:
            self.Time = time.time()
        self.From = FromStr
        self.To = ToStr
        self.Subject = SubjectStr
        self.Topic = TopicStr
        self.Contents = (Body and Body.count("\n")+1 or 0)
        self.Body = Body
        self._msg = " "

        
        if Body:

            msg = "Time-sent: " + str(int(time.time()))
            msg =msg + "\nFrom: " + self.From
            if ToStr:
                msg = msg + "\nTo: " + ToStr
            if SubjectStr:
                msg = msg + "\nSubject: " + SubjectStr
            if TopicStr:
                msg = msg + "\nTopic: " + TopicStr

            msg = msg + "\nContents: " + str(Body.count("\n")+1)
            msg = msg + "\n" + Body

            sha = sha256()
            sha.update(bytes(msg, "utf8"))
            msg = "Message-id: SHA-256 " + sha.hexdigest() + "\n" + msg
            self.ID = sha.hexdigest()
            
            self._msg = msg

    def Parse(self, s):
        a = s.split("\n")
        self.ID = a[0][a[0].find("SHA-256")+8:]
        self.Time = int(a[1][a[1].find(": ")+2:])
        self.From = a[2][a[2].find(": ")+2:]

        for x,y in enumerate(a):
            if y.find("To: ") != -1:
                self.To = y[y.find(": ")+2:]
            elif y.find("Subject: ") != -1:
                self.Subject = y[y.find(": ")+2:]
            elif y.find("Topic: ") != -1:
                self.Topic = y[y.find(": ")+2:]
            elif y.find("Contents: ") != -1:
               self.Contents = y[y.find(": ")+2:]
               a = a[x+1:]

        self.Body = "\n".join(a)

        self._msg = s
        return self

    def HasHeaders(self, HeaderPairs):
        headerValues = {
            "Message-id:" : self.ID,
            "Time-sent:" : self.Time,
            "From:" : self.From,
            "To:" : self.To,
            "Subject:" : self.Subject,
            "Topic:" : self.Topic,
            "Contents:" : self.Contents,
            "Body:" : self.Body
        }

        print(HeaderPairs)

        fail = False
        for HeaderPair in HeaderPairs:
            k = HeaderPair.split(": ")
            Header = k[0]+":"
            Content = k[1]
            try:
                if headerValues[Header] != Content:
                    fail = True
            except:
                fail = True

        return not fail
        
    def __str__(self):
        return self._msg
    
version = 1 #PM version
messages = [
    Message().Parse("""Message-id: SHA-256 bc18ecb5316e029af586fdec9fd533f413b16652bafe079b23e021a6d8ed69aa
Time-sent: 1614686400
From: martin.brain@city.ac.uk
Topic: #announcements
Subject: Hello!
Contents: 2
Hello everyone!
This is the first message sent using PM.""")
]
#stores the first message

validheaders = {
    "From:" : True,
    "To:" : True,
    "Subject:" : True,
    "Topic:" : True,
    "Contents:" : True,
    "Body:" : True
}
#implemented headers 

print("Please ensure a server is running before attempting to connect!")
#wetware sanity test

class SocketClient:
    def __init__(self, addr, port):
        #wraps a socket connection a server at (addr:port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.protostage = 0
        self.timedelta = 0
        self.sentprotocol = False

        self.sock.connect((addr, port))

        self.sendbuffer = []
        self.recvbuffer = []
        self.dead = False

    def _sendinternal(self):
        for i, packet in enumerate(self.sendbuffer):
            #if i == len(self.sendbuffer)-1:
                self.sock.send(packet.encode("utf-8"))
            #else:
            #    self.sock.send((packet+"\\PACKETEND\\").encode("utf-8"))
        self.sendbuffer = []

    def Send(self, strdata):
        self.sendbuffer.append(strdata)
        #self.sock.send(strdata.encode("utf-8"))

    def Recv(self, size):
        if self.dead:
            return
        data = self.sock.recv(size).decode("utf-8")
        self.recvbuffer = data.split("\\PACKETEND\\")
        #print("received data: ", data)

#class that wraps send and recv socket functionality to buffers so that reading and writing is less strictly
#related to buffer states of the socket 

host = input("Enter ip to connect to, (use network ip even if server on localhost to route from router) ")
port = int(input("Enter port to connect on, recommended 20111 "))

client = SocketClient(host, port)
client.Send("PROTOCOL? " + str(version) + " " + str(int((time.time()-int(time.time()))*10000)))
client.sentprotocol = True
#attempts connection to a Server booted and running on host:port
#will not let host be 127.0.0.1 or localhost, must be routed by the network router to be external
#since on windows machines connecting to localhost can cause OSErrors but getting routed by the router is fine

def polluser():
    """
    Threaded function which polls userinput with a delay for responses to be displayed in the terminal.
    May cause issues with synchronisation, in which case run in the console rather than IDLE due to issues with
    GIL (Global Interpreter Lock)

    Allows the user to choose from a list of actions, to achieve different behaviours w.r.t the server.
    """
    #above is a doc comment btw python syntax is cool isnt it... 
    while not client.dead:
        
        time.sleep(1)
        #delay to allow received packets to display withoutt clipping (input) proc 
        opt = 0
        choices = {
                "opt" : opt
            }
        #dict to hold user choices in the current poll

        if client.dead:
            return
        
        p = input("Please choose an action: (1) Sync Time (2) List Messages (3) Get Message (4) Add Message (5) Exit")
        p = "".join(re.findall("[0-9]", p))
        if not (p.isspace() or len(p)==0):
            opt = int(p)
        #get the user choice as an integer, filter out non integer characters
        #avoid whitespace post filter
        #default option 0 will just do nothing aka repeat the poll 

        
        if opt == 1:
            client.Send("TIME?")
            
        elif opt == 2:
            choices["headers"] = {}
            t = input("Please enter a time to get messages since, current time in seconds is " + str(int(time.time())))
            choices["since"] = "".join(re.findall("[0-9]", t))
            while 1:
                k = input("Please enter header to filter, e.g From: martin.brain@city.ac.uk")

                if k.isspace() or len(k) == 0:
                    break
                
                k = k.split(": ")

                header = k[0]+":"
                content = ": ".join(k[1:])

                try:
                    if validheaders[header]:
                        choices["headers"][header] = content
                except:
                    pass

            getstr = "LIST? " + choices["since"] + " " + str(len(choices["headers"]))
            for header, value in choices["headers"].items():
                getstr = getstr + "\n" + header + " " + value
            client.Send(getstr)
        elif opt == 3:
            hash = input("Please enter a message hash to request: ")
            client.Send("GET? " + hash)
        elif opt == 4:
            print("Please enter the message header values, you may leave blank if optional(OPTIONAL)")
            
            From = input("From: ")
            To = input("(OPTIONAL)To: ")
            Subject = input("(OPTIONAL)Subject: ")
            Topic = input("(OPTIONAL)Topic: ")
            Body = input("Message body: ")

            if To.isspace():
                To = None
            if Subject.isspace():
                Subject = None
            if Topic.isspace():
                Topic = None
            
            t = Message(FromStr = From, Body=Body, ToStr=To, SubjectStr=Subject, TopicStr=Topic)
            messages.append(t)
            print("added message!\n" + str(t))
            
        elif opt == 5:
            client.Send("BYE")
            client.dead = True
            client._sendinternal()
            return

t = threading.Thread(target = polluser, args=[], daemon = True)
t.start()
#Start the user input poll on a parallel thread (Not true parallelism, see pythondocs GIL)

while not client.dead:

    read, write, error = select.select([client.sock], [client.sock], [])
    #based on the buffer sort the client into read write lists
    for sock in read:

        client.Recv(65535)
        #receive the buffer size 65535 see Polite Messaging PDF 

        for packet in client.recvbuffer:
            #not properly implemented packet sizes but this'll work for my client and my server....
            #should be programmed better but it's pretty solid, was hard to get multiple packets into the buffer.
            if packet.isspace() or len(packet) == 0:
                break
            #skip empty packets

            terms = packet.split()
            #split terms on whitespace
            if terms[0] == "PROTOCOL?":
                client.protostage = 1
                if not client.sentprotocol:
                    client.Send("PROTOCOL? " + str(version) + " " + str(int((time.time()-int(time.time()))*10000)))
                version = min(int(terms[1]), version)
                #echo protocol and choose maximum shared version A.K.A. smallest of client, server versions. 
            elif terms[0] == "TIME?":
                client.timedelta = float(terms[1]) - time.time()
                client.protostage = 3
                #on receiving a time from the server will bake the time difference to sync the times
                #doesn't handle the server requesting the time, would be a ballache to differentiate
                #a prompt vs response here 
            elif terms[0] == "MESSAGES":
                count = terms[1]
                print("LIST Found:")
                for i in range(int(count)):
                    #iterate messages specified by packet
                    msghash = terms[2+i]
                    print(msghash)
                    #output to client console
                    found = False
                    for m in messages:
                        if m.ID == msghash:
                            found = True
                    if not found:
                        client.Send("GET? " + msghash)
                    #request only messages not already stored in the PM node (client)
                    
            elif terms[0] == "FOUND":
                msgstr = "\n".join((packet.split("\n"))[1:])
                #rebuild the message sub the request string
                msg = Message().Parse(msgstr)
                #Parse the packet as a message
                Found = False
                for m in messages:
                    if m.ID == msg.ID:
                        Found = True
                if not Found:
                    messages.append(msg)
                    print("added message!")
                print(str(msg))
                #if the message isn't already in storage, store itt
                #allows messages to propagate across the network
                
            elif terms[0] == "SORRY":
                print("failed to find message")
                
            elif terms[0]== "LIST?":
                #from example PM1 
                #LIST since headers
                #From: martin.brain@city.ac.uk
                #Topic: #announcements
                since = terms[1]
                headercount = terms[2]
                headerpairs = packet.split("\n")[1:]
                #take all lines after the first, aka lines containing headers
                #doesn't properly handle multiple buffered packets, ought to be corrected 
                matches = []
                for message in messages:
                    if message.HasHeaders(headerpairs) and message.Time >= float(since):
                        matches.append(message.ID)
                #loop messages check for matches, add to a list 

                result = "MESSAGES " + str(len(matches))
                for m in matches:
                    result = result + "\n" + str(m)
                client.Send(result)
                #format the list of found matches and send it
                
            elif terms[0] == "GET?":
                id = terms[1]
                found = False
                for message in messages:
                    if message.ID == id:
                        client.Send("FOUND\n"+str(message))
                        found = True
                        break
                if not found:
                    client.Send("SORRY")
            elif terms[0] == "BYE":
                print("CONNECTION CLOSED")
                client.dead = True
                break

    for sock in write:
       pass

    client._sendinternal()

    
        
