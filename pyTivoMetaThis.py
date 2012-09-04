#!/usr/bin/python
# Copyright (c) 2008, Graham Dunn <gmd@kurai.org>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#    * Neither the name of the author nor the names of the contributors may be used to endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


# Version : $Id: pyTivoMetaThis.py 20 2009-02-22 15:02:39Z gdunn $
# vim: autoindent tabstop=4 expandtab shiftwidth=4


import urllib
import sys
import re
import string
import os
import errno
import sqlite3

from optparse import OptionParser
from xml.etree.ElementTree import parse, Element, SubElement
from time import gmtime, strftime, strptime
from datetime import datetime
# Import the IMDbPY package.
IMDB = ""
try:
	import imdb
except ImportError:
	print 'IMDB module could not be loaded. Movie Lookups will be disabled. See http://imdbpy.sourceforge.net'
	IMDB = "NO"


# Useage:
# pyTivoMetaThis --path "VideoFilesDirectory"
# Flow:
#	Operate on a single directory of files
#	Look for files with filenames like /*SnnEnn*/
#		For each one, get the episode information and write out /(*)SnnEnn(*)/.txt file with metadata.
#

parser = OptionParser()
parser.add_option("-d", "--debug", action="store_true", dest="debug", help="Turn on debugging.")
parser.add_option("-f", "--force", action="store_true", dest="clobber", help="Force overwrite of existing metadata")
parser.add_option("-p", "--path", dest="filedir", default=".", help="The directory containing files to be looked up. Defaults to .")
parser.add_option("-t", "--tidy", action="store_true", dest="metadir", help="Save metadata to the .meta directory in video directory. Compatible with tlc's patch (http://pytivo.krkeegan.com/viewtopic.php?t=153)")
parser.add_option("-m", "--movie", action="store_true", dest="isMovie", help="Look up in the Internet Movie DataBase")
parser.add_option("-a", "--alternate", action="store_true",dest="isAltOutput", help="Enable adding extended information to seriesTitle and title for TV shows and to title for Movies")
parser.add_option("-i", "--interactive", action="store_true",dest="interactive", help="If more than one match, script presents menu to choose correct one")

(options, args) = parser.parse_args()

APIKEY="0403764A0DA51955"

GETSERIESID_URL = '/api/GetSeries.php?'
GETEPISODEID_URL = '/GetEpisodes.php?'
GETEPISODEINFO_URL = '/EpisodeUpdates.php?'
METADIR = ""
if (options.metadir): METADIR = ".meta"

if ( (options.isMovie) and (IMDB == "NO") ):
     print "Cannot lookup movies without IMDB. Exiting."
     sys.exit(1)

# string encoding for input from console
in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
# string encoding for output to console
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()
# string encoding for output to metadata files.  Tivo is UTF8 compatible so use that for file output
file_encoding = 'UTF-8'

if options.debug: 
	print "\nConsole Input encoding: %s" % in_encoding
	print "Console Output encoding: %s" % out_encoding
	print "Metadata File Output encoding: %s\n" % file_encoding

def getMirrorURL():
	# Query tvdb for a list of mirrors
	mirrorsURL = "http://www.thetvdb.com/api/%s/mirrors.xml" % APIKEY
	mirrorsXML = parse(urllib.urlopen(mirrorsURL))
	mirrors = [Item for Item in mirrorsXML.findall('Mirror')]
	mirrorURL = mirrors[0].findtext('mirrorpath')
	return mirrorURL

def getSeriesId(MirrorURL, show_name):
	seriesid = ""
	# Prepare the seriesID file
	seriesidpath = options.filedir + os.sep + show_name + ".seriesID"
	if options.debug: print "Looking for .seriesID file in " + seriesidpath.encode(out_encoding, 'replace')
	
	# Get seriesid
	if os.path.exists(seriesidpath):
		if options.debug: print "Opening existing %s" % seriesidpath.encode(out_encoding, 'replace')
		seriesidfile = open(seriesidpath, 'r')
		seriesid = seriesidfile.read()
		seriesidfile.close()

	if ( (not options.clobber) and (len(seriesid) > 0)  ):
		seriesid = re.sub("\n", "", seriesid)
		if options.debug: print "Read seriesID %s from %s" % (seriesid.encode(out_encoding, 'replace'), seriesidpath.encode(out_encoding, 'replace'))
	else:
		if options.debug: print "Searching for series with name %s" % show_name.encode(out_encoding, 'replace')

		url = MirrorURL + GETSERIESID_URL + urllib.urlencode({"seriesname" : show_name})
		if options.debug: print "seriesXML: Using URL" , url

		seriesXML = parse(urllib.urlopen(url)).getroot()

		series = [Item for Item in seriesXML.findall('Series')]

		# Display all the shows found 

		if(len(series) > 2):
			print "####################################\n"
			print "Multiple TV Shows found:\n"
			print "Found %s shows for Series Title %s" % (len(series), show_name.encode(out_encoding, 'replace'))
			print "------------------------------------"
			for e in series:
				eSeriesName = e.findtext('SeriesName')
				eId = e.findtext('id')
				eOverview = e.findtext('Overview')
				# eOverview may not exist, so default them to something so print doesn't fail
				if(eOverview is None):
					eOverview = "<None>"
				if(len(eOverview) > 240):
					eOverview = eOverview[0:239]
				print "Series Name:\t%s\nSeries ID:\t%s\nDescription:\n\n%s\n------------------------------------" % \
				(eSeriesName.encode(out_encoding, 'replace'), eId.encode(out_encoding, 'replace'), eOverview.encode(out_encoding, 'replace'))
			print "####################################\n\n"
			seriesid = raw_input('Please choose the correct seriesid: ')

		else:
			seriesid = series[0].findtext('id')

		if options.debug: print "Creating %s" % seriesidpath.encode(out_encoding, 'replace')
		seriesidfile = open(seriesidpath, 'w')
		seriesidfile.write(seriesid)
		seriesidfile.close()

	seriesURL = MirrorURL + "/api/" + APIKEY + "/series/" + seriesid + "/en.xml"
	if (options.debug): print "getSeriesInfoXML: Using URL " + seriesURL
	seriesURLXML  = parse(urllib.urlopen(seriesURL)).getroot()

	return seriesURLXML, seriesid

def getEpisodeInfoXML(MirrorURL, seriesid, season, episode):
	# Takes a seriesid, season number, episode number and return xml data`

	url = MirrorURL + "/api/" + APIKEY + "/series/" + seriesid + "/default/" + season + "/" + episode + "/en.xml"
	if options.debug: print "getEpisodeInfoXML: Using URL" , url
	episodeInfoXML = parse(urllib.urlopen(url)).getroot()

	if (options.debug):
		print "Returning episodeInfoXML:"
		print str(episodeInfoXML)

	return episodeInfoXML

def formatEpisodeData(e, f):
	# Takes a dict e of XML elements, the series title, the Zap2It ID (aka the Tivo groupID), and a filename f
	# TODO : Split up multiple guest stars / writers / etc. Split on '|'. (http://trac.kurai.org/trac.cgi/ticket/2)
	# This is weak. Should just detect if EpisodeNumber exists.
	if (options.debug) : print "In formatEpisodeData\n"
	metadataText = []
	isE = "true"
	e["isEpisode"] = isE

	# The following is a dictionary of pyTivo metadata attributes and how they map to thetvdb xml elements. 
	pyTivoMetadata = {
		# As seen on http://pytivo.armooo.net/wiki/MetaData
		'time' : 'time',
		'originalAirDate' : 'FirstAired',
		'seriesTitle' : 'SeriesName',
		'title' : 'EpisodeName',
		'description' : 'Overview',
		'isEpisode' : 'isEpisode',
		'seriesId' : 'zap2it_id',
        'episodeNumber' : 'EpisodeNumber',
		'displayMajorNumber' : 'displayMajorNumber',
        'callsign' : 'callsign',
        'showingBits' : 'showingBits',
        'displayMinorNumber' : 'displayMinorNumber',
		'startTime' : 'startTime',
		'stopTime' : 'stopTime',
		'tvRating' : 'tvRating',
		'vProgramGenre' : 'Genre',
		'vSeriesGenre' : 'Genre',
        'vActor' : 'Actors',
        'vGuestStar' : 'GuestStars',
		'vDirector' : 'Director',
        'vExecProducer' : 'ExecProducer',
        'vWriter' : 'Writer',
		'vHost' : 'Host',
		'vChoreographer' : 'Choreographer',
	}
	
	# These are thetvdb xml elements that have no corresponding Tivo metadata attribute. Maybe someday.
	unused = {
		'id' : 'id',
		'seasonid' : 'seasonid',
		'ProductionCode' : 'ProductionCode',
		'ShowURL' : 'ShowURL',
		'lastupdated' : 'lastupdated',
		'flagged' : 'flagged',
		'DVD_discid' : 'DVD_discid',
		'DVD_season' : 'DVD_season',
		'DVD_episodenumber' : 'DVD_episodenumber',
		'DVD_chapter' : 'DVD_chapter',
		'absolute_number' : 'absolute_number',
		'filename' : 'filename',
		'lastupdatedby' : 'lastupdatedby',
		'mirrorupdate' : 'mirrorupdate',
		'lockedby' : 'lockedby',
		'SeasonNumber': 'SeasonNumber'
	}
    
	#for pyTivoTag in pyTivoMetadata.keys():
	#	print "%s : %s" % (pyTivoTag, pyTivoMetadata[pyTivoTag])
	
	# pyTivo Metadata tag order
	
	pyTivoMetadataOrder = [
		'seriesTitle',
		'title',
		'originalAirDate',
		'description',
		'isEpisode',
		'seriesId',
		'episodeNumber',
		'vProgramGenre',
		'vSeriesGenre',
		'vDirector',
		'vWriter',
		'vGuestStar',
		'vActor'
	]
	
	for tvTag in pyTivoMetadataOrder:
		
		if (options.debug): print "Working on %s" % tvTag
		
		if ( pyTivoMetadata.has_key(tvTag) and (pyTivoMetadata[tvTag]) and e.has_key(pyTivoMetadata[tvTag]) and (e[pyTivoMetadata[tvTag]]) ):
			# got data to work with
			line = ""
			safeline = ""

			transtable = { 
				8217 : u'\'',
				8216 : u'\'',
				8220 : u'\"',
				8221 : u'\"'
			}
			
			stripped = unicode(e[pyTivoMetadata[tvTag]]).translate(transtable)

			# for debugging character translations
			#if ( tvTag == 'description'):
			#	print "ord -> %s" % ord(stripped[370])
			
			text = stripped.encode(file_encoding, 'replace')
			textdebug = stripped.encode(out_encoding, 'replace')
			
			if (options.debug): print "%s : %s" % (tvTag, textdebug)
			
			if ( tvTag == 'originalAirDate' ):
				text = datetime(*strptime(text, "%Y-%m-%d")[0:6]).strftime("%Y-%m-%dT%H:%M:%SZ")
			
			if ( options.isAltOutput and tvTag == 'seriesTitle' and pyTivoMetadata.has_key('title') and (pyTivoMetadata['title']) and e.has_key(pyTivoMetadata['title']) and (e[pyTivoMetadata['title']]) ):
				text = "%s S%02dE%02d %s" % ( text, int(e['SeasonNumber']), int(e['EpisodeNumber']), e[pyTivoMetadata['title']].encode(file_encoding, 'replace') )
			
			if ( options.isAltOutput and tvTag == 'title' ):
			
				text = "S%02dE%02d %s" % ( int(e['SeasonNumber']), int(e['EpisodeNumber']), text )
			
			if '|' in text:
				people = text.strip('|').split('|')
				for person in people:
					if (options.debug): print "Splitting " + person.strip()
					
					line += "%s : %s\n" % (tvTag, re.sub('\n', ' ', person.strip()))
			else:
				line = "%s : %s\n" %(tvTag, re.sub('\n', ' ', text))
				if (options.debug): print "Completed -> %s" % line.decode(file_encoding, 'replace').encode(out_encoding, 'replace')
			
			metadataText.append(line)

		else:
			if (options.debug): print "No data for %s" % tvTag
		
	if (len(metadataText) > 1):
		outFile = open(f, 'w')
		outFile.writelines(metadataText)
		outFile.close()

def formatMovieData(title, f):

	safeline = ""
	line = ""
	metadataText = []

	objIA = imdb.IMDb() # create new object to access IMDB
	title = unicode(title, in_encoding, 'replace')
	try:
		# Do the search, and get the results (a list of Movie objects).
	        results = objIA.search_movie(title)
	except imdb.IMDbError, e:
		print "Complete error report:"
		print e
		sys.exit(3)
		
	if not results:
		print 'No matches for "%s", sorry.' % title.encode(out_encoding, 'replace')
		return

	if (options.interactive):

		# Get number of movies found
		num_titles = len(results)
		
		# If only one found, select and go on
		if (num_titles == 1):
			movie = results[0]
		else:
			# Show max 5 titles
			if (num_titles > 5 ):
				num_titles = 5;

			#print "Found %s matches for /'%s/'\n" % (len(results), title.encode(out_encoding, 'replace'))
			print "\nMatches for '%s'\n" % (title.encode(out_encoding, 'replace'))
			print "------------------------------------"
			print "Num\tTitle"
			print "------------------------------------"
		
			for i in range(0, num_titles):
				m_title = results[i]['long imdb title']
				print "%d\t%s" % (i, m_title.encode(out_encoding, 'replace'))
		
			print ""

			movie_num = raw_input('Please choose the correct movie [0]: ')

			if (movie_num):  #check for null string
				movie_num = int(movie_num)
			else: 
				movie_num = 0
		
			movie = results[movie_num]

			print "------------------------------------"
		
	else: # automatically pick first match
		# This is a Movie instance.
		movie = results[0]

		# Print only the first result.
		if (options.debug): print '--->Best match for "%s" is "%s"' % (title.encode(out_encoding, 'replace'), str(movie))
	
	# So far the Movie object only contains basic information like the
	# title and the year; retrieve main information:

	objIA.update(movie)

	#print movie.summary()
	
	# title
	if (options.isAltOutput):
		line += "title : %s (%s)\n" % (movie['title'].encode(file_encoding, 'replace'), movie['year'].encode(file_encoding, 'replace'))
	else:
		line += "title : %s\n" % movie['title'].encode(file_encoding, 'replace')

	# movieYear
	line += "movieYear : %s\n" % movie['year'].encode(file_encoding, 'replace')
	# description
	if ( "plot outline" in movie.keys()):
		line += "description : %s" % movie['plot outline'].encode(file_encoding, 'replace')
		# IMDB score if available
		if ( "rating" in movie.keys()):
			line += " - IMDB Score: %s out of 10" % movie['rating']
		line += "\n"
	elif ( "rating" in movie.keys()):
		# no description, but have IMDB score
		line += "description : IMDB Score: %s out of 10\n" % movie['rating']
	
	# isEpisode always false for movies
	line += "isEpisode : false\n"
	# starRating
	if ("rating" in movie.keys()):
		line += "starRating : "
		starCalc = .4 * movie['rating']
		# testing value
		#starCalc = 3.6
		if( starCalc <= 1.0 ):
			line += "x1"
		elif ( (starCalc > 1.0) and (starCalc <= 1.5) ):
			line += "x2"
		elif ( (starCalc > 1.5) and (starCalc <= 2.0) ):
			line += "x3"
		elif ( (starCalc > 2.0) and (starCalc <= 2.5) ):
			line += "x4"
		elif ( (starCalc > 2.5) and (starCalc <= 3.0) ):
			line += "x5"
		elif ( (starCalc > 3.0) and (starCalc <= 3.5) ):
			line += "x6"
		elif ( (starCalc > 3.5) ):
			line += "x7"
	
		line += "\n"
	# mpaaRating
	# kind of a hack for now...
	# maybe parsing certificates would work better?
	if ("mpaa" in movie.keys()):
		mpaaStr = movie['mpaa']
		# testing value
		#mpaaStr = "Rated "
		mpaaRating = ""
		
		if   ("Rated G " in mpaaStr):
			mpaaRating = "G1"
		elif ("Rated PG " in mpaaStr):
			mpaaRating = "P2"
		elif ("Rated PG-13 " in mpaaStr):
			mpaaRating = "P3"
		elif ("Rated R " in mpaaStr):
			mpaaRating = "R4"
		elif ("Rated X " in mpaaStr):
			mpaaRating = "X5"
		elif ("Rated NC-17 " in mpaaStr):
			mpaaRating = "N6"
		
		if mpaaRating:
			line += "mpaaRating : %s\n" % mpaaRating
		
	#vProgramGenre and vSeriesGenre
	if ("genres" in movie.keys()):
		for i in movie['genres']:
			line += "vProgramGenre : %s\n" % i.encode(file_encoding, 'replace')
		for i in movie['genres']:		
			line += "vSeriesGenre : %s\n" % i.encode(file_encoding, 'replace')

	#don't enable the next line unless you want the full cast, actors + everyone else who worked on the movie
	#objIA.update(movie, 'full credits')

	# vDirector (suppress repeated names)
	if ("director" in movie.keys()):
		directors = {}
		for i in movie['director']:
			if (not directors.has_key(i['name'])):
				directors[i['name']] = 1
				line += "vDirector : %s\n" % i['name'].encode(file_encoding, 'replace')
				if (options.debug): print "vDirector : %s" % i.get('name').encode(out_encoding, 'replace')
	# vWriter (suppress repeated names)
	if ("writer" in movie.keys()):
		writers = {}
		for i in movie['writer']:
			if (not writers.has_key(i['name'])):
				writers[i['name']] = 1
				line += "vWriter : %s\n" % i['name'].encode(file_encoding, 'replace')
				if (options.debug): print "vWriter : %s" % i.get('name').encode(out_encoding, 'replace')
	# vActor (suppress repeated names)
	if ("cast" in movie.keys()):
		actors = {}
		for i in movie['cast']:
			if (not actors.has_key(i['name'])):
				actors[i['name']] = 1				
				line += "vActor : %s\n" % i.get('name').encode(file_encoding, 'replace')
				if (options.debug): print "vActor : %s" % i.get('name').encode(out_encoding, 'replace')
		
	if (options.debug): print "\nWriting to %s\n" % f.encode(out_encoding, 'replace')
	outFile = open(f, 'w')
	outFile.writelines(line)
	outFile.close()
		       										
			
def writeData(e):
	# currently, we're doing this in the formatEpisodeData function
	return 0

def getfiles(directory, fileExtList):
		"Get list of file info objects for files of particular extensions"
		#fileList = [os.path.split(os.path.normcase(f))[1] for f in os.listdir(directory)]
		fileList = os.listdir(directory)
		if (options.debug): print "fileList before cull: %s" % str(fileList)
		fileList = [f for f in fileList if os.path.splitext(f)[1].lower() in fileExtList]
		if (options.debug): print "fileList after cull: %s" % str(fileList)
		return fileList

def main():

	# Initalize things we'll need for looking up data
	MirrorURL = getMirrorURL()
	# conn = sqlite3.connect('db/pyTivMetaThis.db')

	# Types of files we want to get metadata for

	fileExtList = [".mpg", ".avi", ".ogm", ".mkv", ".mp4", ".mov", ".wmv"]


	for filename in getfiles(options.filedir, fileExtList):
		if (options.debug): print "\n--->working on: %s\n" % filename.encode(out_encoding, 'replace')
		if (options.isMovie):
			# in movie mode, ignore TV files since IMDB info on them isn't useful
			match = re.search('(.*).[Ss](\d\d)[Ee](\d\d).*', filename)
			if (match):
				if (options.debug): print "Movie mode: Ignoring TV show %s\n" % filename.encode(out_encoding, 'replace')
				continue

			match = os.path.splitext(filename)[0]
			if match is None:
				continue

			# in some cases I was getting the subdir name on there,
			# so let's just strip it off
			if (options.filedir != "."):
				title = re.sub(options.filedir, '', match)
			else:
				title = re.sub('[\\._]', ' ', match)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')

			# strip a variety of common junk from torrented avi filenames
			# these first are case-sensitive
			title = re.sub('crowbone', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('joox-dot-net', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('DOMiNiON', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('LiMiTED', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('aXXo', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('DoNE', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('ViTE', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('BaLD', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('leetay', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('\.AC3', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('\[Eng\]', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('\[AC3\]', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			# this gets rid of the bracketed year
			title = re.sub('\[\d\d\d\d\]', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			# now lower-case it for some general stuff
			title = string.lower(title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			# periods and dashes become spaces
			title = re.sub('[\\._-]', ' ', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('swesub', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('dvdrip', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('dvdscr', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('xvid', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('divx', '', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			# clear out space runs
			title = re.sub('  ', ' ', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			title = re.sub('  ', ' ', title)
			if options.debug: print "After filter, title is: " + title.encode(out_encoding, 'replace')
			
		else:
			match = re.search('(.*).[Ss](\d\d)[Ee](\d\d).*', filename)
			if match is None:
				continue
				
			series = re.sub('[\\._]', ' ', match.group(1))
			season = str(int(match.group(2)))
			episode = str(int(match.group(3)))

		if (METADIR):
			if (options.debug): print "Metadir is: %s" % METADIR.encode(out_encoding, 'replace')
			try:
				# os.makedirs will also create all the parent directories
				os.makedirs(METADIR)
			except OSError, err:
				if err.errno == errno.EEXIST:
					if os.path.isdir(METADIR):
						if (options.debug): print "directory already exists"
					else:
						if (options.debug): print "file already exists, but not a directory"
						raise # re-raise the exception
				else:
					raise
			metadataFileName = os.path.join(METADIR, filename + ".txt")
		else:
			metadataFileName = os.path.join(options.filedir, filename + ".txt")	
		
		if ((options.clobber) or (not os.path.exists(metadataFileName))):
			if (options.isMovie):
				if (options.debug): print "Writing information for %s in IMDB to %s" % (title.encode(out_encoding, 'replace'), metadataFileName.encode(out_encoding, 'replace'))
				formatMovieData(title, metadataFileName)
			else:
				if (options.debug): print "Series: %s\nSeason: %s Episode: %s" % (series.encode(out_encoding, 'replace'), season, episode)
				
				episodeInfo = {}
				
				(seriesInfoXML, seriesid) = getSeriesId(MirrorURL, series)
				
				for node in seriesInfoXML.getiterator():
					episodeInfo[node.tag] = node.text
				
				episodeInfoXML = getEpisodeInfoXML(MirrorURL, seriesid, season, episode)

				for node in episodeInfoXML.getiterator():
					episodeInfo[node.tag] = node.text
                	
				formatEpisodeData(episodeInfo, metadataFileName)

if __name__ == "__main__":
	main()
