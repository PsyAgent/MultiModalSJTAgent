import os
import itertools
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_audioclips

class AVMerger:
    def __init__(self, video_folder, audio_folder, output_folder):
        self.video_folder = video_folder
        self.audio_folder = audio_folder
        self.output_folder = output_folder

    def merge(self, num_files=None, only_first_pair: bool = False, output_basename: str | None = None):
        # Check if the output folder exists, create it if not
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        video_files = self._get_video_files()
        audio_files = self._get_audio_files()

        if num_files is not None:
            video_files = video_files[:num_files]
            audio_files = audio_files[:num_files]

        print(f"Total number of video files: {len(video_files)}")
        print(f"Total number of audio files: {len(audio_files)}")
        print()

        pairs = list(zip(video_files, audio_files))
        if only_first_pair and pairs:
            pairs = [pairs[0]]

        for idx, (video_path, audio_path) in enumerate(pairs, start=1):
            try:
                video_clip = VideoFileClip(video_path)
                audio_clip = AudioFileClip(audio_path)
                merged_clip = video_clip.set_audio(audio_clip)

                # Output name: prefer provided basename; else derive from video name
                if output_basename:
                    # if batching, add index suffix to avoid overwrite
                    name = output_basename if only_first_pair else f"{output_basename}_{idx}"
                    output_filename = f"{name}.mp4"
                else:
                    output_filename = f"merged_{os.path.basename(video_path).replace(' ', '_')}"
                output_path = os.path.join(self.output_folder, output_filename)
                merged_clip.write_videofile(output_path, codec='libx264')

                print(
                    f"Merged [{os.path.basename(video_path)}] with [{os.path.basename(audio_path)}] successfully.\nSaved to: {os.path.basename(output_path)}")

            except Exception as e:
                print(f"Failed to merge {video_path} with {audio_path}: {e}")

    def _get_video_files(self):
        video_files = []
        for filename in os.listdir(self.video_folder):
            if filename.endswith(".mp4"):
                video_files.append(os.path.join(self.video_folder, filename))
        return sorted(video_files)

    def _get_audio_files(self):
        audio_files = []
        for filename in os.listdir(self.audio_folder):
            if filename.endswith(".mp3"):
                audio_files.append(os.path.join(self.audio_folder, filename))
        num_audio_files = len(audio_files)
        num_video_files = len(self._get_video_files())
        # Repeat audio files to match the number of video files
        repeated_audio_files = audio_files * (num_video_files // num_audio_files) + audio_files[
                                                                                    :num_video_files % num_audio_files]
        return repeated_audio_files



if __name__ == "__main__":
    video_folder = r"E:\博士学习\GitHUB_demo\SJTAgent-main\test"  # e.g. "D:/Users/username/Desktop/videos"
    audio_folder = r"E:\博士学习\GitHUB_demo\SJTAgent-main\test"  # e.g. "E:/Users/username/Desktop/audios"
    output_folder = r"E:\博士学习\GitHUB_demo\SJTAgent-main\test"  # e.g. "F:/Users/username/Desktop/merged_videos"

    # Set test mode and specify the number of files to process
    test_mode = False
    # test_mode = True
    num_files_to_process = 3

    merger = AVMerger(video_folder, audio_folder, output_folder)
    merger.merge(num_files=num_files_to_process if test_mode else None, only_first_pair=False, output_basename=None)
