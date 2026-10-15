<?php

namespace App\Jobs;

use App\Models\Song;
use FFMpeg\Format\Video\X264;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Queue\SerializesModels;
use ProtoneMedia\LaravelFFMpeg\Support\FFMpeg;

class SongHlsProcess implements ShouldQueue
{
    use Queueable, SerializesModels, Dispatchable;
    protected $songId;

    /**
     * Create a new job instance.
     */
    public function __construct($songId)
    {
        $this->songId = $songId;
    }

    /**
     * Execute the job.
     */
    public function handle(): void
    {
        $song = Song::findOrFail($this->songId);
        $aac = new X264("aac");
        $fileName = "playlist.m3u8";
        $filePath = "songs/hls_" . $song->id;
        FFMpeg::fromDisk('s3')->open($song->raw_song_path)->exportForHLS()->addFormat($aac)->setSegmentLength(10)->toDisk('s3')->save($filePath . "/" . $fileName);
        $duration = FFMpeg::fromDisk('s3')->open($song->raw_song_path)->getDurationInSeconds();
        $song->update([
            'song_path' => $filePath . '/' . $fileName,
            'duration' => $duration
        ]);
    }
}
