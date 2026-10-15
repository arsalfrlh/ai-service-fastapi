<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;
use Override;

#[Table("songs")]
#[Fillable(['title','artis_name','thumbnail_path','song_path','raw_song_path','duration','lyric','lyric_segments'])]

class Song extends Model
{
    #[Override]
    protected function casts()
    {
        return [
            'lyric_segments' => 'array'
        ];
    }
}
