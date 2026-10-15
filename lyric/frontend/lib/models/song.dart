import 'package:toko/models/lyric_segment.dart';

class Song {
  final int id;
  final String title;
  final String artisName;
  final String thumbnailPath;
  final String? songPath;
  final String rawSongPath;
  final int duration;
  final String? lyric;
  final List<LyricSegment> lyricSegments;

  Song({required this.id, required this.title, required this.artisName, required this.thumbnailPath, this.songPath, required this.rawSongPath, required this.duration, this.lyric, required this.lyricSegments});
  factory Song.fromJson(Map<String, dynamic> json){
    return Song(
      id: json['id'],
      title: json['title'],
      artisName: json['artis_name'],
      thumbnailPath: json['thumbnail_path'],
      songPath: json['song_path'],
      rawSongPath: json['raw_song_path'],
      duration: json['duration'],
      lyric: json['lyric'],
      lyricSegments: json['lyric_segments'] != null ? (json['lyric_segments'] as List).map((item) => LyricSegment.fromJson(item)).toList() : []
    );
  }
}