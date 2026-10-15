<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('songs', function (Blueprint $table) {
            $table->integer('id')->primary()->autoIncrement();
            $table->string('title');
            $table->string('artis_name');
            $table->string('thumbnail_path');
            $table->string('song_path')->nullable();
            $table->string('raw_song_path');
            $table->integer('duration')->default(0);
            $table->text('lyric')->nullable();
            $table->json('lyric_segments')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('songs');
    }
};
