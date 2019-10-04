import requests
import json
import xmltodict
import asyncio
from aiohttp import CookieJar, ClientSession
import traceback

class VideoScraper:

	SCOREBOARD_URL_BASE = 'https://stats.nba.com/stats/scoreboardV2'
	SCOREBOARD_URL_PARAMS = ['DayOffset', 'LeagueID', 'gameDate']

	PLAYBYPLAY_URL_BASE = 'https://stats.nba.com/stats/playbyplayv2'
	PLAYBYPLAY_URL_PARAMS = ['EndPeriod', 'EndRange', 'GameID', 'RangeType', 'Season', 'SeasonType', 'StartPeriod', 'StartRange']
	
	VIDEO_EVENT_URL_BASE = 'https://stats.nba.com/stats/videoevents'
	VIDEO_EVENT_URL_PARAMS = ['GameEventID', 'GameID']
	
	VIDEO_XML_URL_BASE = 'https://secure.nba.com/video/wsc/league/'

	VIDEO_MP4_URL_BASE = 'https://pmd.cdn.turner.com'

	def __init__(self, config):
		self.config = config
		self.session = None
		self.tasks = []

	async def run(self):
		while True:
			if len(self.tasks) > 0:
				task = self.tasks.pop()
				try:
					await asyncio.sleep(0.5)
					await task
				except Exception as e:
					traceback.print_tb(e.__traceback__)

	async def scrape(self, url, expectedParams, actualParams, dataFormat, timeout):
		
		if not self.validateParameters(expectedParams, actualParams):
			raise RuntimeError('Query parameters invalid')

		queryString = self.getQueryString(actualParams)
		url += queryString

		print('[VideoScraper::scrape] {}'.format(url))

		headers = { 'User-Agent': '', 'Cookie': 'AMCV_248F210755B762187F000101%40AdobeOrg=1687686476%7CMCIDTS%7C18172%7CvVersion%7C3.0.0; check=true; ak_bmsc=03BEE504793B8529CBEB413E7FB248B3B81960C7184A0000720B955D0DD13D42~plAgkRIRDBGugecrE/sJj5w5Jo1GepUGN+UdV9/Z7gdtmu+M5ACv9mdJ12Cgl1dlqZTUxH9JR8WqBW2q7Ie5HpIMPPXNrBEb1j+wLZD/fX92QOLAp05OWLKgZZ+OxnIamyyJ8J7EqmNpv7VfZiaZ2TCl7HGf8ea3hZNE8mS2t/yR/k1zmYAZf9fPt9DoG5MeUxNUKld8lD1QgCbQO1n/U9ZlFdJHuNzM7EamZXxxIclW4=' }
		async with ClientSession() as session:
			async with session.get(url, headers = headers, timeout = timeout) as response:
				response = await response.read()

		return self.parse(response, dataFormat)

	def parse(self, rawData, dataFormat):
		try: 
			if dataFormat == 'JSON':
				return json.loads(rawData)
			elif dataFormat == 'XML':
				return xmltodict.parse(rawData)
			else:
				return rawData
		except Exception as e:
			raise e
	
	async def scrapeScoreBoard(self, dayOffset, leagueID, gameDate):
		params = { 'DayOffset': dayOffset, 'LeagueID': leagueId, 'gameDate': gameDate }
		return await self.scrape(VideoScraper.SCOREBOARD_URL_BASE, VideoScraper.SCOREBOARD_URL_PARAMS, params, 'JSON', 1.0)
 
	async def scrapePlayByPlay(self, filter, endPeriod, endRange, gameId, rangeType, season, seasonType, startPeriod, startRange):
		params = { 'EndPeriod': endPeriod, 'EndRange': endRange, 'GameID': gameId, 'RangeType': rangeType, 'Season': season, 'SeasonType': seasonType, 'StartPeriod': startPeriod, 'StartRange': startRange }
		response = await self.scrape(VideoScraper.PLAYBYPLAY_URL_BASE, VideoScraper.PLAYBYPLAY_URL_PARAMS, params, 'JSON', 15.0)
		
		for play in response['resultSets'][0]['rowSet']:
			if VideoScraper.playByPlayFilter(filter, play):
				gameId, gameEventId = play[0], play[1]
				task = asyncio.ensure_future(self.scrapeVideoEvent(gameEventId, gameId))
				self.tasks.append(task)

		return response

	@staticmethod
	def playByPlayFilter(filter, play):
		playerFilter = filter['player']
		playTypeFilter = filter['type']

		return play[13] in playerFilter and play[2] in playTypeFilter


	async def scrapeVideoEvent(self, gameEventId, gameId):
		params = {'GameEventID': gameEventId, 'GameID': gameId }

		response = await self.scrape(VideoScraper.VIDEO_EVENT_URL_BASE, VideoScraper.VIDEO_EVENT_URL_PARAMS, params, 'JSON', 15.0)
		
		if len(response['resultSets']['Meta']['videoUrls']) == 0:
			return {}
		else:
			videoUUId = response['resultSets']['Meta']['videoUrls'][0]['uuid']
			task = asyncio.ensure_future(self.scrapeVideoInfoXML(gameId, gameEventId, videoUUId))
			self.tasks.append(task)

		return response
		
	async def scrapeVideoInfoXML(self, gameId, gameEventId, videoUUId):
		response = await self.scrape(VideoScraper.VIDEO_XML_URL_BASE + videoUUId + '.secure.xml', list(), dict(), 'XML', 15.0)
		if response == {}:
			return

		files = response['video']['files']
	
		print(files)

		videoMp4Urls = []
		for k, v in files.items():
			for z in v:
				if '#text' in z:
					if 'turner.com' in z['#text'] and '1080' in z['#text']:
						videoMp4Urls.append(z['#text'])
		
		if (len(videoMp4Urls) == 0):
			return {}

		task = asyncio.ensure_future(self.scrapeVideoMP4(gameId, gameEventId, videoUUId, videoMp4Urls[0]))
		self.tasks.append(task)
		
		return response
	
	async def scrapeVideoMP4(self, gameId, gameEventId, videoUUId, videoUrl):
		fileName = '{}.mp4'.format(videoUUId)

		async with ClientSession() as session:
			async with session.get(videoUrl, chunked = 4096) as response:
				print('[VideoScraper::scrape] {}'.format(videoUrl))
				with open('vids/{}'.format(fileName), 'wb') as outputFile:
					async for chunk in response.content.iter_chunked(4096):
						if chunk:
							outputFile.write(chunk)
		return fileName

	def validateParameters(self, expectedParams, actualParams):
		for p in expectedParams:
			if (not p in actualParams) or (actualParams[p] is None):
				return False

		return True

	def getQueryString(self, params):
		queryString = '?'
		
		for p in params:
			queryString += '{}={}&'.format(p, params[p])

		return queryString[:-1]
