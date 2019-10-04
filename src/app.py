from scraper import VideoScraper
import json
import asyncio

class App:
	def __init__(self, config):
		self.config = config
		self.scraper = VideoScraper({})
	
	def run(self):
		
		filter = {
			'player': set([202695]),
			'type': set([1, 2, 3, 4, 5])
		}

		task = asyncio.ensure_future(self.scraper.scrapePlayByPlay(filter, 10, 55800, '0021800549', 2, '2018-2019', 'Playoffs', 0, 0))
		self.scraper.tasks.append(task)

		loop = asyncio.get_event_loop()	
		loop.run_until_complete(self.scraper.run())
app = App({})

app.run()
