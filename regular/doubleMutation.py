#Double Mutation created by William Tian on May 21st, 2020.
#Uses multiMutant.sh (which in also depends upon ProMute) to mutate a given PDB ID twice.
#The results are consolidated into a file called "D_<PDBID><Chain><Range>_out"
#Redundant results are removed entirely, but the program still goes through the process of creating them.
#This is done through the use of a trie, and examining the FASTA sequences for each PDB
#The trie is created from the file trieHelper.py.
#doubleMutation.py is dependent on trieHelper for deleting redundant sequences.

import sys
import os
import time
import requests
#from trieHelper import *

#Macros
TEMP_F = "temp_doubleMutationHelper" #Name of the temporary directory where we store the singly mutated sequences.

#You can swap between one or the other by commenting and uncommenting out the few lines of code below when we use
#one of these data structures. In experience, the Map seems slightly faster.
#PDB_T = trieHelper() #Our trie
PDB_DICT = {} #A map

def echoPWD():
    print(os.popen('echo $PWD').read())

#Returns the path for the folder outputed by multiMutant.sh. It'll look like "<ID><CHAIN><RANGE>_out"
def getPath(argv):
    return argv[1] + argv[2] + argv[3] + '_out'

def createDir(t_f):
    if(os.path.exists(t_f)):
        os.system('rm -rf ' + t_f)
    os.system('mkdir ' + t_f)    

def getRange(argv):
    r = argv[3].split(':')
    return [int(r[0]), int(r[1])]
    
#First insert is the original FASTA sequence. With this mutations back into the original sequence are redundant.
def initializeTrie(pdbID, start, end):
    response = requests.get('https://www.rcsb.org/fasta/entry/' + pdbID).text.split()
    #trieHelper.insertNode(PDB_T, response[len(response) - 1][start - 1: end].lower())
    PDB_DICT[response[len(response) - 1][start - 1: end].lower()] = ""
    
#We only want to compare the part of the FASTA sequence that can be changed.
#The range given from the command line argument is not 0 indexed, so we subtract 1 from the start
def getFASTA(fileName, start, end):
    with open(fileName) as f:
        #print(f.read()[start - 1: end])
        return f.read()[start - 1: end]

#Deletes the leftover files from multiMutant. I thought they were annoying.
def cleanMultiMutant(argv):
    os.system('rm -rf ' + getPath(argv))

    #Commenting this out so you don't have to redownload the PDB file every time you want to call on the same sequence
    #os.system('rm promute/' + argv[1] + '.pdb')
    
#Mutates a given sequence with the given parameters.
#argv[0] is never used. argv[1] is the PDB ID.
#argv[2] is the Chain (Note: Case sensitive). argv[3] is the range (Note: Inclusive on both ends).
#Essentially just calls ./multiMutant.sh with the command line arguments passed
def callMultiMutant(argv, seq = "", em="", hphilic="", hphobic=""):
    fPath = getPath(argv)
    os.system('rm -rf ' + fPath)

    #print('Calling ./multiMutant.sh ' + argv[1] + ' ' + argv[2] + ' ' + argv[3] + ' ' + em + hphilic + hphobic) 

    os.popen('./multiMutant.sh ' + argv[1] + ' ' + argv[2] + ' ' + argv[3] + ' ' + em + hphilic + hphobic).read()  
    os.system('find ./' + fPath + ' -type d -empty -delete') #Removes redundant folders   

#MultiMutant.sh creates a bunch of PDB files across multiple folders in a new directory.
#This gathers all those files and puts them into a single temporary folder. Specified by t_f.
#This new folder will be discarded once the PDB files are mutated again, giving the original sequence two mutations.
#Inserts into a trie or map so future singly mutated sequences are removed
def gatherPDBs(argv, t_f):
    fPath = getPath(argv)
    r = getRange(argv)
    createDir(t_f)
    
    os.chdir('./' + fPath)
    for dirs in os.walk('.', topdown = False):
        if dirs[0] != '.':
            fileName = dirs[0] + '/' + dirs[0] + '.fasta.txt'
            PDB_DICT[getFASTA(fileName, r[0], r[1]).lower()] = ""
            #trieHelper.insertNode(PDB_T, getFASTA(fileName, r[0], r[1]).lower())
            os.system('mv ' + dirs[0] + '/' + dirs[0] + '.pdb' + ' ../' + t_f)
    os.chdir('..')
    
#Moves the entire folder of sequences into one main folder.
def gatherDoubles(argv, t_f):
    fPath = getPath(argv)
    os.system('mv ' + fPath + '/* ' + t_f)
    os.system('rm -rf ' + fPath + ' ' + t_f + '/sequentialPipelineInvocation.sh')

#Uses PDB_T, a trie, (or PDB_DICT, a map) to check if a FASTA sequence is found. If it is, we remove the folder, as it's redundant.
#We get the FASTA sequence with getFASTA(), and use r, the range, to specify a substring to grab
def removeRedundants(workingDir, argv):
    print("Removing redundant sequences...")
    os.chdir(workingDir)
    
    i, j = 0, 0
    r = getRange(argv)
    initializeTrie(argv[1], r[0], r[1])
    for dirs in os.walk('.', topdown = False):
        if(dirs[0] != '.'):
            seq = getFASTA(dirs[0] + '/' + dirs[0] + '.fasta.txt', r[0], r[1]).lower()
            if seq in PDB_DICT:
            #if trieHelper.insertNode(PDB_T, seq) == True: #If True then we remove, since it's a redundant sequence
                os.system('rm -rf ' + dirs[0])
                i += 1
            else:
                PDB_DICT[seq] = ""
            j += 1
    os.chdir('..') #Changes back to the root directory for this file
    os.system('rm -rf ' + TEMP_F) #Removes the temporary folder which we used for our singly mutated sequences
    print("\nRemoved %d redundant sequences out of %d total sequences." % (i, j))
    print("There are now %d sequences total." % (j - i))
    
# Grabs the temporary directory, and mutates everything in it again. This is where we do our second mutation
#Those results are then moved into the final directory, under the variable "dir"
def mutateDirectory(argv, em = "", hphilic = "", hphobic = ""):
    dir = 'D_' + argv[1] +  argv[2] + argv[3] + '_out'
    createDir(dir)
    
    for file in os.listdir(TEMP_F):
        if file.endswith(".pdb"):
            os.system('mv ' + TEMP_F + '/' + file + ' promute') #Moves the current file in the loop into ./promute/
            file = file.replace('.pdb', '')
            temp_argv = [0, file, argv[2], argv[3]] #Create a new argv, with the PDB ID as the file we just obtained
            callMultiMutant(temp_argv, em, hphilic, hphobic )
            os.system('rm ./promute/' + file + '.pdb')

            gatherDoubles(temp_argv, dir)
    
def main():
    if(len(sys.argv) < 4):
        sys.exit("Please enter the correct command line arguments")
    r = getRange(sys.argv)
    if(r[0] == r[1]):
        sys.exit("This script doesn't do single mutations and the range specified is one. Use multiMutant.sh instead.")

    
    sys.argv[1] = sys.argv[1].upper()
    sys.argv[2] = sys.argv[2].upper()
    #Checking for flags
    emFlag, hphilicFlag, hphobicFlag = "","",""
    for i in range(4, len(sys.argv)):
        flag = sys.argv[i].lower()
        if(flag == "-em"):
            emFlag = flag + " "
        elif(flag == "-hphilic"):
            hphilicFlag = flag + " "
        elif(flag == "-hphobic"):
            hphobicFlag = flag + " "

    startTime = time.time()
    print("Grabbing PDB files and mutating...")
    
    callMultiMutant(sys.argv)
    gatherPDBs(sys.argv, TEMP_F)
    mutateDirectory(sys.argv, emFlag, hphilicFlag, hphobicFlag)
    
    midTime = time.time()
    removeRedundants('D_' + getPath(sys.argv), sys.argv)
    cleanMultiMutant(sys.argv)

    print("\nTime spent grabbing and mutating: %f minutes" % ((midTime - startTime) / 60))
    print("Time spent removing redundant sequences: %f minutes" % ((time.time() - midTime) / 60))
    print("Total time elapsed: %f minutes" % ((time.time() - startTime) / 60))

    print("\nFolder is D_" + getPath(sys.argv))
    
if __name__ == "__main__":
    main()
