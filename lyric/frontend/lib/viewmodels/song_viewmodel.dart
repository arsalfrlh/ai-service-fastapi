import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import 'package:toko/models/song.dart';
import 'package:toko/services/api_service.dart';
import 'package:toko/services/song_service.dart';

class SongViewmodel extends ChangeNotifier {
  final _apiService = ApiService();
  final _songService = SongService();
  AudioPlayer get player => _songService.player;
  List<Song> songList = [];
  List<Song> recentlyPlayed = [];
  bool isLoading = false;
  Song? currentSong;
  String? message;
  
  SongViewmodel(){
    _songService.player.processingStateStream.listen((p){
      if(p == ProcessingState.completed){
        final index = songList.indexWhere((s) => s.id == currentSong?.id);
        if(index >= 0 && index < songList.length - 1){
          skipToNext();
        }
      }
    });
    notifyListeners();
  }

  Future<void> fetchSong()async{
    isLoading = true;
    notifyListeners();
    songList = await _apiService.getAllSong();
    isLoading = false;
    notifyListeners();
  }

  Future<void> playSong(Song song)async{
    recentlyPlayed.removeWhere((s) => s.id == song.id);
    recentlyPlayed.insert(0, song);
    if (recentlyPlayed.length > 10){
      recentlyPlayed.removeLast();
    }
    if(song.id == currentSong?.id){
      return;
    }
    currentSong = song;
    await _songService.setSource(song.songPath ?? song.rawSongPath);
    notifyListeners();
  }

  Future<bool> uploadSong(String title, String artisName, String thumbnailPath, String songPath, String? language)async{
    isLoading = true;
    message = null;
    notifyListeners();
    final response = await _apiService.uploadSong(title, artisName, thumbnailPath, songPath, language);
    isLoading = false;
    message = response['message'];
    notifyListeners();
    return(response['success'] as bool);
  }

  void play() => _songService.play();
  void pause() => _songService.pause();
  void seek(Duration value) => _songService.seek(value);

  Future<void> skipToPrevious() async {
    final index = songList.indexWhere((song) => song.id == currentSong?.id);
    if (index > 0) {
      await playSong(songList[index - 1]);
    }
  }

  Future<void> skipToNext() async {
    final index = songList.indexWhere((song) => song.id == currentSong?.id);
    if (index >= 0 && index < songList.length - 1) {
      await playSong(songList[index + 1]);
    }
  }
}