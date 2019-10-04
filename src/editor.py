import os
from moviepy.editor import VideoFileClip, concatenate_videoclips

class VideoEditor:
	def __init__(self, config):
		self.config = config

	def concat(self, clipFilenames, outputFilename, destroyClips):
		
		clips = [ VideoFileClip(f) for f in clipFilenames ]
		
		outputClip = concatenate_videoclips(clips)
		outputClip.write_videofile(outputFilename, threads=8)

		return outputFilename


editor = VideoEditor({})

files = []

for v in os.listdir('vids'):
	files.append('vids/' + v)

print(files)
editor.concat(files, 'highlights.mp4', False)
