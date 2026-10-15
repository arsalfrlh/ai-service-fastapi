import 'package:toko/models/lyric_word.dart';

class LyricSegment {
  final int index;
  final String text;
  final int startMillisecond;
  final int endMillisecond;
  final List<LyricWord> words;

  LyricSegment({
    required this.index,
    required this.text,
    required this.startMillisecond,
    required this.endMillisecond,
    required this.words,
  });

  factory LyricSegment.fromJson(Map<String, dynamic> json) {
    final words = ((json['words'] as List?) ?? [])
        .map((item) => LyricWord.fromJson(item))
        .toList();

    return LyricSegment(
      index: json['id'],
      text: json['text'],
      // Fallback ke timestamp kata kalau server tidak mengirim start_ms/end_ms
      startMillisecond: (json['start_ms'] as int?) ??
          (words.isNotEmpty ? words.first.startMillisecond : 0),
      endMillisecond: (json['end_ms'] as int?) ??
          (words.isNotEmpty ? words.last.endMillisecond : 0),
      words: words,
    );
  }
}