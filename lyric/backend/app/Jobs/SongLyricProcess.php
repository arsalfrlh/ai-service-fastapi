<?php

namespace App\Jobs;

use App\Models\Song;
use Exception;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Throwable;

class SongLyricProcess implements ShouldQueue
{
    use Queueable, SerializesModels, Dispatchable;
    protected $aiApiKey;
    protected $aiBaseUrl;
    protected $songId;
    protected $language;

    /**
     * Create a new job instance.
     */
    public function __construct($songId, $language = null)
    {
        $this->aiApiKey = config('ai.ai_api_key');
        $this->aiBaseUrl = config('ai.ai_base_url');
        $this->songId = $songId;
        $this->language = $language;
    }

    /**
     * Execute the job.
     */
    public function handle(): void
    {
        set_time_limit(0);
        $song = Song::findOrFail($this->songId);
        try{
            $response = Http::timeout(600)->withHeaders([
                'kwanzx-key' => $this->aiApiKey
            ])->post($this->aiBaseUrl . "/convert",[
                'id' => $song->id,
                'file_path' => $song->raw_song_path,
                'language' => $this->language
            ]);

            $json = $response->json();
            if(!$response->successful()){
                throw new Exception("Fail for request to API");
            }
            $song->update([
                'lyric' => $json['data']['text'],
                'lyric_segments' => $json['data']['segments']
            ]);
            Log::info($json['message'], $json);
        }catch(Throwable $e){
            Log::error($e->getMessage(), $song->toArray());
        }
    }
}
