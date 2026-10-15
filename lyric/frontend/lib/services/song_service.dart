import 'package:just_audio/just_audio.dart';

class SongService {
  final _player = AudioPlayer();
  AudioPlayer get player => _player;

  Future<void> setSource(String songPath)async{
    await _player.stop();
    await _player.setUrl("http://10.0.2.2:9000/songs/$songPath");
    _player.play();
  }

  void play() => _player.play();
  void pause() => _player.pause();
  void seek(Duration value) => _player.seek(value);
}