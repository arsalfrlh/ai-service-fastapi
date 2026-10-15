class LyricWord {
  final String word;
  final int startMillisecond;
  final int endMillisecond;

  LyricWord({required this.word, required this.startMillisecond, required this.endMillisecond});
  factory LyricWord.fromJson(Map<String, dynamic> json){
    return LyricWord(
      word: json['text'],
      startMillisecond: json['start_ms'],
      endMillisecond: json['end_ms']
    );
  }
}