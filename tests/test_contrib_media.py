import asyncio
import os
import tempfile
import wave
from unittest import TestCase

import cv2
import numpy

from aiortc import AudioStreamTrack, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder
from aiortc.mediastreams import MediaStreamError

from .utils import run


class MediaTestCase(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.directory.cleanup()

    def create_audio_file(self, name, channels=1, sample_rate=8000, sample_width=2):
        path = self.temporary_path(name)

        writer = wave.open(path, 'wb')
        writer.setnchannels(channels)
        writer.setframerate(sample_rate)
        writer.setsampwidth(sample_width)

        writer.writeframes(b'\x00' * sample_rate * sample_width * channels)
        writer.close()

        return path

    def create_video_file(self, name, width=640, height=480, fps=30, duration=1):
        path = self.temporary_path(name)

        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(path, fourcc, fps, (width, height))

        frames = duration * fps
        for i in range(frames):
            s = i * 256 // frames
            pixel = (s, 256 - s, (128 - 2 * s) % 256)
            image = numpy.full((height, width, 3), pixel, numpy.uint8)
            out.write(image)
        out.release()

        return path

    def temporary_path(self, name):
        return os.path.join(self.directory.name, name)


class MediaBlackholeTest(TestCase):
    def test_audio(self):
        recorder = MediaBlackhole()
        recorder.addTrack(AudioStreamTrack())
        recorder.start()
        run(asyncio.sleep(1))
        recorder.stop()

    def test_audio_ended(self):
        track = AudioStreamTrack()

        recorder = MediaBlackhole()
        recorder.addTrack(track)
        recorder.start()
        run(asyncio.sleep(1))
        track.stop()
        run(asyncio.sleep(1))

        recorder.stop()

    def test_audio_remove_track(self):
        recorder = MediaBlackhole()
        track = AudioStreamTrack()
        recorder.addTrack(track)
        recorder.start()
        run(asyncio.sleep(1))
        recorder.removeTrack(track)
        run(asyncio.sleep(1))
        recorder.stop()

    def test_audio_and_video(self):
        recorder = MediaBlackhole()
        recorder.addTrack(AudioStreamTrack())
        recorder.addTrack(VideoStreamTrack())
        recorder.start()
        run(asyncio.sleep(2))
        recorder.stop()

    def test_video(self):
        recorder = MediaBlackhole()
        recorder.addTrack(VideoStreamTrack())
        recorder.start()
        run(asyncio.sleep(2))
        recorder.stop()

    def test_video_ended(self):
        track = VideoStreamTrack()

        recorder = MediaBlackhole()
        recorder.addTrack(track)
        recorder.start()
        run(asyncio.sleep(1))
        track.stop()
        run(asyncio.sleep(1))

        recorder.stop()


class MediaPlayerTest(MediaTestCase):
    def test_audio_file_8kHz(self):
        path = self.create_audio_file('test.wav')
        player = MediaPlayer(path=path)

        # check tracks
        self.assertIsNotNone(player.audio)
        self.assertIsNone(player.video)

        # read all frames
        self.assertEqual(player.audio.readyState, 'live')
        for i in range(49):
            frame = run(player.audio.recv())
            self.assertEqual(frame.format.name, 's16')
            self.assertEqual(frame.layout.name, 'mono')
            self.assertEqual(frame.samples, 960)
            self.assertEqual(frame.sample_rate, 48000)
        with self.assertRaises(MediaStreamError):
            run(player.audio.recv())
        self.assertEqual(player.audio.readyState, 'ended')

        # try reading again
        with self.assertRaises(MediaStreamError):
            run(player.audio.recv())

    def test_audio_file_48kHz(self):
        path = self.create_audio_file('test.wav', sample_rate=48000)
        player = MediaPlayer(path=path)

        # check tracks
        self.assertIsNotNone(player.audio)
        self.assertIsNone(player.video)

        # read all frames
        self.assertEqual(player.audio.readyState, 'live')
        for i in range(50):
            frame = run(player.audio.recv())
            self.assertEqual(frame.format.name, 's16')
            self.assertEqual(frame.layout.name, 'mono')
            self.assertEqual(frame.samples, 960)
            self.assertEqual(frame.sample_rate, 48000)
        with self.assertRaises(MediaStreamError):
            run(player.audio.recv())
        self.assertEqual(player.audio.readyState, 'ended')

    def test_video_file(self):
        path = self.create_video_file('test.avi', duration=3)
        player = MediaPlayer(path=path)

        # check tracks
        self.assertIsNone(player.audio)
        self.assertIsNotNone(player.video)

        # read all frames
        self.assertEqual(player.video.readyState, 'live')
        for i in range(90):
            frame = run(player.video.recv())
            self.assertEqual(frame.width, 640)
            self.assertEqual(frame.height, 480)
        with self.assertRaises(MediaStreamError):
            run(player.video.recv())
        self.assertEqual(player.video.readyState, 'ended')


class MediaRecorderTest(MediaTestCase):
    def test_audio_mp3(self):
        recorder = MediaRecorder(path=self.temporary_path('test.mp3'))
        recorder.addTrack(AudioStreamTrack())
        recorder.start()
        run(asyncio.sleep(2))
        recorder.stop()

    def test_audio_wav(self):
        recorder = MediaRecorder(path=self.temporary_path('test.wav'))
        recorder.addTrack(AudioStreamTrack())
        recorder.start()
        run(asyncio.sleep(2))
        recorder.stop()

    def test_audio_wav_ended(self):
        track = AudioStreamTrack()

        recorder = MediaRecorder(path=self.temporary_path('test.wav'))
        recorder.addTrack(track)
        recorder.start()
        run(asyncio.sleep(1))
        track.stop()
        run(asyncio.sleep(1))

        recorder.stop()

    def test_audio_and_video(self):
        recorder = MediaRecorder(path=self.temporary_path('test.mp4'))
        recorder.addTrack(AudioStreamTrack())
        recorder.addTrack(VideoStreamTrack())
        recorder.start()
        run(asyncio.sleep(2))
        recorder.stop()

    def test_video_jpg(self):
        recorder = MediaRecorder(path=self.temporary_path('test-%3d.jpg'))
        recorder.addTrack(VideoStreamTrack())
        recorder.start()
        run(asyncio.sleep(2))
        recorder.stop()

    def test_video_mp4(self):
        recorder = MediaRecorder(path=self.temporary_path('test.mp4'))
        recorder.addTrack(VideoStreamTrack())
        recorder.start()
        run(asyncio.sleep(2))
        recorder.stop()
