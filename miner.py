#!/usr/bin/env python

# -*- Python 2.7 -*-

import os
import sys
import time
import datetime
import json
import commands
import httplib
import requests

from urllib import urlopen



gRigName = "-"
gJsonSite = "-"
gDebugMode = 0
gGpuNotHashing = 0
gLogFile = "/home/ethos/gpu_crash.log"

# ================================ pushsafer.com Informations =============================

gPrivateKey = "gPrivateKey"

'''
- Vous devez creer un compte ici https://www.pushsafer.com/ puis, confirmer votre adresse mail ;
- Apres que cela soit fait, rendez vous ici https://www.pushsafer.com/en/apps pour installer l application sur vos smartphones ;
- Quand l'application est installe, ouvrez la et allez ici: https://www.pushsafer.com/en/profile vous pourrez ainsi flasher le QR code et enregistrer votre smartphone ;
- Direction https://www.pushsafer.com/en/dashboard, recuperez-y votre cle prive  Pushsafer et renseignez la plus haut ligne 38.

'''

# ================================  functions  =============================
def DumpActivity(dumpStr):
  print dumpStr

  try:
    # writes input string in a file
    pLogFile = open(gLogFile, "a")
    pLogFile.write("%s @ %s\n" % (dumpStr, str(datetime.datetime.now())))
    pLogFile.close()
  except:
    print "File write error in - " + gLogFile



# ============================== process arguments ============================
def ProcessArguments(gotPanelInfo):
  # arg#0: rig name (required if "/var/run/ethos/stats.file" not available)
  # arg#1: json site (required if "/var/run/ethos/url.file" not available)
  # "-debug" : (optional) set debug mode
  global gRigName, gJsonSite, gDebugMode

  if (gotPanelInfo != 1):
    DumpActivity("Taking rig name and panel url from arguments")

  argStr = ""

  argIdx = 0
  argProcessed = 0
  while (1):
    argIdx += 1
    if (argIdx >= len(sys.argv)):
      break

    arg = sys.argv[argIdx]

    if (str(arg) == "-debug"):
      gDebugMode = 1
      DumpActivity("debug mode")
      continue

    if (gotPanelInfo == 1):
      DumpActivity("Ignoring argument : " + str(arg))
      continue

    argProcessed += 1
    if (argProcessed == 1):
      gRigName = arg
    elif(argProcessed == 2):
      gJsonSite = arg
  

def GetPanelInfo():
  global gRigName, gJsonSite

  commandOutput = commands.getstatusoutput('\grep http /var/run/ethos/url.file')
  if (commandOutput[0] != 0):
    DumpActivity("/var/run/ethos/url.file is not availble")
    return 0

  gJsonSite = commandOutput[1]
  gJsonSite = gJsonSite+"/?json=yes"

  commandOutput = commands.getstatusoutput("\grep hostname /var/run/ethos/stats.file")
  if (commandOutput[0] != 0):
    DumpActivity("/var/run/ethos/stats.file is not avaible")
    return 0

  gRigName = commandOutput[1][9:]

  return 1



# ===================================   run  ================================
success = GetPanelInfo()
ProcessArguments(success)
DumpActivity("Rig name: " + gRigName + ", Json: " + gJsonSite)

while 1:
  # wait for 4 min
  time.sleep(240)

  # read site content
  try:
    url = urlopen(gJsonSite).read()
  except:
    DumpActivity("invalid url")
    continue

  # convert site content to json
  try:
    result = json.loads(url)
  except:
    DumpActivity("invalid json")
    continue

  # extract data
  try:
    numGpus = result["rigs"][gRigName]["gpus"]
    numRunningGpus = result["rigs"][gRigName]["miner_instance"]
    hashRate =  result["rigs"][gRigName]["miner_hashes"]
    status = result["rigs"][gRigName]["condition"]
  except:
    DumpActivity("invalid rig name")
    continue

  if (str(gDebugMode) == "1"):
    DumpActivity("<" + status + "> Gpus: " + str(numRunningGpus) + "/" + str(numGpus) + " - " + str(hashRate))

  if (status == "unreachable"):
    gGpuNotHashing = 0
    DumpActivity("[Warning] panel is not updating")
    continue;

  # check if any gpu is down
  if (int(numRunningGpus) != int(numGpus)):
    if (gGpuNotHashing == 1):

      url = 'https://www.pushsafer.com/api' # URL de destination
      post_fields = {
              "t" : "RIG: " + gRigName + " rebooting", # Titre de la notification
              "m" : "Your rig : " + gRigName + " rebooting due to low HashRate: " + hashRate + ".", # Message (corp) de la notification
              "s" : "",
              "v" : "",
              "i" : "37",
              "c" : "",
              "d" : "a",
              "u" : gJsonSite.split('.')[0] + ".ethosdistro.com/graphs/?rig=" + gRigName + "&type=miner_hashes", # URL pour Android & IOS
              "ut" : "Open graphs link", # Titre de l'URL
              "k" : gPrivateKey} # Private key qui doit etre rensigne ligne 38

      result = requests.post(url, data=post_fields)
      DumpActivity(result)

      # reboot
      DumpActivity("Rebooting (" + str(hashRate) + ")")
      os.system("sudo reboot")
    else:
      # wait for another 2 min before rebooting
      DumpActivity("One or more Gpu(s) might have crashed")
      gGpuNotHashing = 1
  else:
    # reset reboot pending counter
    gGpuNotHashing = 0
