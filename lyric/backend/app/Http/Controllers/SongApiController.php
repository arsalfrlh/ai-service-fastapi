<?php

namespace App\Http\Controllers;

use App\Jobs\SongHlsProcess;
use App\Jobs\SongLyricProcess;
use App\Models\Song;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;

class SongApiController extends Controller
{
    public function index(){
        $data = Song::all();
        return response()->json(['message' => "Menampilkan semua lagu", 'success' => true, 'data' => $data], 200);
    }

    public function store(Request $request){
        $validator = Validator::make($request->all(),[
            'title' => 'required',
            'artis_name' => 'required',
            'thumbnail_file' => 'required|image|mimes:jpg,jpeg,png',
            'song_file' => 'required|file|mimes:mp3,wav',
            'language' => 'string|nullable'
        ]);

        if($validator->fails()){
            return response()->json(['message' => $validator->errors()->all(), 'success' => true], 422);
        }
        // dd($request->toArray());

        $thumbnail = $request->file('thumbnail_file');
        $thumbnailName = "thumbnail" . time() . '.' . $thumbnail->getClientOriginalExtension();
        $thumbnailPath = $thumbnail->storeAs('thumbnails',$thumbnailName,'s3');
        
        $song = $request->file('song_file');
        $songName = "song_" . time() . '.' . $song->getClientOriginalExtension();
        $songPath = $song->storeAs('songs/raw',$songName,'s3');
        $data = Song::create([
            'title' => $request->title,
            'artis_name' => $request->artis_name,
            'thumbnail_path' => $thumbnailPath,
            'raw_song_path' => $songPath
        ]);

        SongHlsProcess::dispatch($data->id);
        SongLyricProcess::dispatch($data->id, $request->language ?? null);
        return response()->json(['message' => "Lagu berhasil diupload", 'success' => true, 'data' => $data], 201);
    }
}
