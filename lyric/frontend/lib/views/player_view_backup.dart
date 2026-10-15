// import 'package:flutter/material.dart';
// import 'package:provider/provider.dart';
// import 'package:toko/models/lyric_segment.dart';
// import 'package:toko/models/lyric_word.dart';
// import 'package:toko/models/song.dart';
// import 'package:toko/viewmodels/song_viewmodel.dart';

// //MINIPLAYER
// class PlayerView extends StatelessWidget {
//   const PlayerView({super.key});

//   @override
//   Widget build(BuildContext context) {
//     final songVM = Provider.of<SongViewmodel>(context);
    
//     return songVM.currentSong == null
//     ? const SizedBox()
//     : GestureDetector(
//         onTap: () {
//           showModalBottomSheet(
//             context: context,
//             isScrollControlled: true,
//             backgroundColor: Colors.transparent,
//             builder: (_) => FullPlayer(
//               onClose: () => Navigator.pop(context),
//             ),
//           );
//         },
//         child: const _MiniPlayerContainer(),
//       );
//   }
// }

// class _MiniPlayerContainer extends StatelessWidget {
//   const _MiniPlayerContainer();

//   @override
//   Widget build(BuildContext context) {
//     return Container(
//       height: 95,
//       margin: const EdgeInsets.all(12),
//       padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
//       decoration: BoxDecoration(
//         gradient: LinearGradient(
//           colors: [
//             Colors.orange.shade600.withOpacity(.95),
//             Colors.orange.shade400.withOpacity(.95),
//           ],
//         ),
//         borderRadius: BorderRadius.circular(22),
//         boxShadow: [
//           BoxShadow(
//             color: Colors.orange.shade300.withOpacity(.5),
//             blurRadius: 18,
//             offset: const Offset(0, 6),
//           ),
//         ],
//       ),
//       child: const Row(
//         children: [
//           _MiniArtwork(),
//           SizedBox(width: 14),
//           Expanded(child: _MiniInfo()),
//           SizedBox(width: 12),
//           _MiniControlButton(),
//         ],
//       ),
//     );
//   }
// }

// class _MiniArtwork extends StatelessWidget {
//   const _MiniArtwork();

//   @override
//   Widget build(BuildContext context) {
//     final song =
//         context.select<SongViewmodel, Song?>((vm) => vm.currentSong);

//     return RepaintBoundary(
//       child: ClipRRect(
//         borderRadius: BorderRadius.circular(14),
//         child: song?.thumbnailPath != null
//             ? Image.network(
//                 "http://127.0.0.1:9000/songs/${song!.thumbnailPath}",
//                 width: 62,
//                 height: 62,
//                 fit: BoxFit.cover,
//                 gaplessPlayback: true,
//                 filterQuality: FilterQuality.low,
//               )
//             : const Icon(Icons.music_note, size: 62),
//       ),
//     );
//   }
// }

// class _MiniInfo extends StatelessWidget {
//   const _MiniInfo();

//   @override
//   Widget build(BuildContext context) {
//     final songVM = Provider.of<SongViewmodel>(context);

//     return Column(
//       crossAxisAlignment: CrossAxisAlignment.start,
//       mainAxisAlignment: MainAxisAlignment.center,
//       children: [
//         Text(
//           songVM.currentSong?.title ?? "Unknown",
//           style: const TextStyle(
//             color: Colors.white,
//             fontSize: 16,
//             fontWeight: FontWeight.bold,
//           ),
//           maxLines: 1,
//           overflow: TextOverflow.ellipsis,
//         ),
//         if (songVM.currentSong?.artisName != null) ...[
//           const SizedBox(height: 4),
//           Text(
//             songVM.currentSong!.artisName,
//             style: const TextStyle(
//               fontSize: 13,
//               color: Colors.white70,
//             ),
//           ),
//         ],
//         const SizedBox(height: 8),
//         const _MiniProgress(),
//       ],
//     );
//   }
// }

// class _MiniProgress extends StatelessWidget {
//   const _MiniProgress();

//   @override
//   Widget build(BuildContext context) {
//     final vm = context.watch<SongViewmodel>();

//     return StreamBuilder<Duration?>(
//       stream: vm.player.durationStream,
//       builder: (context, snapshot) {
//         final duration = snapshot.data ?? Duration.zero;
//         return StreamBuilder<Duration>(
//           stream: vm.player.positionStream,
//           builder: (context, snapshot) {
//             final position = snapshot.data ?? Duration.zero;
//             final progress = duration.inMilliseconds == 0
//             ? 0.0
//             : (position.inMilliseconds / duration.inMilliseconds).clamp(0.0, 1.0);
//             return ClipRRect(
//               borderRadius: BorderRadius.circular(20),
//               child: LinearProgressIndicator(
//                 value: progress,
//                 minHeight: 4,
//                 color: Colors.white,
//                 backgroundColor: Colors.white30,
//               ),
//             );
//           },
//         );
//       },
//     );
//   }
// }

// class _MiniControlButton extends StatelessWidget {
//   const _MiniControlButton();

//   @override
//   Widget build(BuildContext context) {
//     final vm = context.read<SongViewmodel>();

//     return StreamBuilder<bool>(
//       stream: vm.player.playingStream,
//       builder: (context, snapshot) {
//         final isPlaying = snapshot.data ?? false;
//         return IconButton(
//           onPressed: () =>
//               isPlaying ? vm.pause() : vm.play(),
//           icon: Icon(
//             isPlaying
//                 ? Icons.pause_circle_filled
//                 : Icons.play_circle_fill,
//             color: Colors.white,
//             size: 42,
//           ),
//         );
//       },
//     );
//   }
// }

// //FULLPLAYER

// class FullPlayer extends StatefulWidget {
//   final VoidCallback onClose;

//   const FullPlayer({
//     super.key,
//     required this.onClose,
//   });

//   @override
//   State<FullPlayer> createState() => _FullPlayerState();
// }

// class _FullPlayerState extends State<FullPlayer> {
//   bool _showLyrics = false;

//   @override
//   Widget build(BuildContext context) {
//     final song = context.select<SongViewmodel, Song?>(
//       (vm) => vm.currentSong,
//     );

//     return FractionallySizedBox(
//       heightFactor: 0.95,
//       child: Container(
//         decoration: const BoxDecoration(
//           gradient: LinearGradient(
//             colors: [
//               Color(0xFFFFA726),
//               Color(0xFFFF7043),
//             ],
//             begin: Alignment.topCenter,
//             end: Alignment.bottomCenter,
//           ),
//           borderRadius: BorderRadius.vertical(
//             top: Radius.circular(26),
//           ),
//         ),
//         child: SafeArea(
//           child: Column(
//             children: [
//               _PlayerHeader(
//                 onClose: widget.onClose,
//               ),

//               // Ganti cover dengan lirik ketika tombol ditekan.
//               Expanded(
//                 child: _showLyrics && song != null
//                     ? _LyricsPanel(song: song)
//                     : const _PlayerArtwork(),
//               ),

//               const _PlayerInfo(),

//               const _PlayerProgress(),

//               // Tombol untuk beralih antara cover dan lirik.
//               TextButton.icon(
//                 onPressed: () {
//                   setState(() {
//                     _showLyrics = !_showLyrics;
//                   });
//                 },
//                 icon: Icon(
//                   _showLyrics ? Icons.album : Icons.lyrics,
//                   color: Colors.white,
//                 ),
//                 label: Text(
//                   _showLyrics
//                       ? 'Show Album Cover'
//                       : 'Show Lyrics',
//                   style: const TextStyle(
//                     color: Colors.white,
//                     fontWeight: FontWeight.w600,
//                   ),
//                 ),
//                 style: TextButton.styleFrom(
//                   padding: const EdgeInsets.symmetric(
//                     horizontal: 18,
//                     vertical: 8,
//                   ),
//                 ),
//               ),

//               const _PlayerControls(),

//               const SizedBox(height: 20),
//             ],
//           ),
//         ),
//       ),
//     );
//   }
// }

// class _PlayerHeader extends StatelessWidget {
//   final VoidCallback onClose;
//   const _PlayerHeader({required this.onClose});

//   @override
//   Widget build(BuildContext context) {
//     return Padding(
//       padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
//       child: Row(
//         children: [
//           Container(
//             width: 40,
//             height: 5,
//             decoration: BoxDecoration(
//               color: Colors.white38,
//               borderRadius: BorderRadius.circular(12),
//             ),
//           ),
//           const Spacer(),
//           IconButton(
//             onPressed: onClose,
//             icon: const Icon(Icons.close, color: Colors.white),
//           ),
//         ],
//       ),
//     );
//   }
// }

// class _PlayerArtwork extends StatelessWidget {
//   const _PlayerArtwork();

//   @override
//   Widget build(BuildContext context) {
//     final song =
//         context.select<SongViewmodel, Song?>((vm) => vm.currentSong);

//     final size = MediaQuery.of(context).size.width * 0.75;

//     return RepaintBoundary(
//       child: Center(
//         child: ClipRRect(
//           borderRadius: BorderRadius.circular(24),
//           child: song?.thumbnailPath != null
//               ? Image.network(
//                   "http://127.0.0.1:9000/songs/${song!.thumbnailPath}",
//                   width: size,
//                   height: size,
//                   fit: BoxFit.cover,
//                   gaplessPlayback: true,
//                   filterQuality: FilterQuality.low,
//                 )
//               : Container(
//                   width: size,
//                   height: size,
//                   color: Colors.black26,
//                   child: const Icon(
//                     Icons.music_note,
//                     size: 80,
//                     color: Colors.white,
//                   ),
//                 ),
//         ),
//       ),
//     );
//   }
// }

// class _PlayerInfo extends StatelessWidget {
//   const _PlayerInfo();

//   @override
//   Widget build(BuildContext context) {
//     final song = context.watch<SongViewmodel>();

//     return Padding(
//       padding: const EdgeInsets.symmetric(vertical: 16),
//       child: Column(
//         children: [
//           Text(
//             song.currentSong?.title ?? "Unknown",
//             style: const TextStyle(
//               fontSize: 22,
//               fontWeight: FontWeight.bold,
//               color: Colors.white,
//             ),
//             maxLines: 1,
//             overflow: TextOverflow.ellipsis,
//           ),
//           const SizedBox(height: 6),
//           Text(
//             song.currentSong?.artisName ?? "Unknown Artist",
//             style: const TextStyle(
//               color: Colors.white70,
//               fontSize: 15,
//             ),
//           ),
//         ],
//       ),
//     );
//   }
// }

// class _PlayerProgress extends StatefulWidget {
//   const _PlayerProgress();

//   @override
//   State<_PlayerProgress> createState() => _PlayerProgressState();
// }

// class _PlayerProgressState extends State<_PlayerProgress> {
//   double? _dragValue;

//   String _format(Duration d) {
//     final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
//     final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
//     return "$m:$s";
//   }

//   @override
//   Widget build(BuildContext context) {
//     final vm = context.watch<SongViewmodel>();

//     return Padding(
//       padding: const EdgeInsets.symmetric(horizontal: 22),
//       child: StreamBuilder<Duration?>(
//         stream: vm.player.durationStream, 
//         builder:(context, snapshot) {
//           final duration = snapshot.data ?? Duration.zero;
//           return StreamBuilder<Duration>(
//             stream: vm.player.positionStream,
//             builder: (context, snapshot) {
//               final position = snapshot.data ?? Duration.zero;
//               return Column(
//                 children: [
//                   Row(
//                     mainAxisAlignment: MainAxisAlignment.spaceBetween,
//                     children: [
//                       Text(_format(position),
//                           style: const TextStyle(color: Colors.white70)),
//                       Text(_format(duration),
//                           style: const TextStyle(color: Colors.white70)),
//                     ],
//                   ),
//                   Slider(
//                     min: 0,
//                     max: duration.inMilliseconds.toDouble(),
//                     value: position.inMilliseconds.clamp(0, duration.inMilliseconds).toDouble(),
//                     activeColor: Colors.white,
//                     inactiveColor: Colors.white38,
//                     onChanged: (value) {
//                       setState(() => _dragValue = value);
//                     },
//                     onChangeEnd: (value) {
//                       vm.seek(Duration(milliseconds: value.toInt()));
//                       _dragValue = null;
//                     },
//                   )
//                 ],
//               );
//             }
//           );
//         }
//       )
//     );
//   }
// }

// class _PlayerControls extends StatelessWidget {
//   const _PlayerControls();

//   @override
//   Widget build(BuildContext context) {
//     final vm = context.watch<SongViewmodel>();

//     return Row(
//       mainAxisAlignment: MainAxisAlignment.center,
//       children: [
//         IconButton(
//           onPressed: vm.skipToPrevious,
//           icon: const Icon(Icons.skip_previous,
//               size: 38, color: Colors.white),
//         ),
//         const SizedBox(width: 20),
//         StreamBuilder<bool>(
//           stream: vm.player.playingStream,
//           builder: (context, snapshot) {
//             final isPlaying = snapshot.data ?? false;
//             return GestureDetector(
//               onTap: () =>
//                   isPlaying ? vm.pause() : vm.play(),
//               child: Icon(
//                 isPlaying
//                     ? Icons.pause_circle
//                     : Icons.play_circle_fill,
//                 size: 70,
//                 color: Colors.white,
//               ),
//             );
//           },
//         ),
//         const SizedBox(width: 20),
//         IconButton(
//           onPressed: vm.skipToNext,
//           icon:
//               const Icon(Icons.skip_next, size: 38, color: Colors.white),
//         ),
//       ],
//     );
//   }
// }


// class _LyricsPanel extends StatefulWidget {
//   final Song song;

//   const _LyricsPanel({
//     required this.song,
//   });

//   @override
//   State<_LyricsPanel> createState() => _LyricsPanelState();
// }

// class _LyricsPanelState extends State<_LyricsPanel> {
//   // Key setiap baris diperlukan untuk auto-scroll.
//   final Map<int, GlobalKey> _lineKeys = {};

//   int? _lastAutoScrollIndex;

//   @override
//   void didUpdateWidget(covariant _LyricsPanel oldWidget) {
//     super.didUpdateWidget(oldWidget);

//     // Reset state apabila lagu berganti.
//     if (oldWidget.song.id != widget.song.id) {
//       _lineKeys.clear();
//       _lastAutoScrollIndex = null;
//     }
//   }

//   // Mencari baris lirik berdasarkan posisi audio.
//   int _findActiveSegmentIndex(
//     List<LyricSegment> segments,
//     int positionMs,
//   ) {
//     int activeIndex = -1;

//     for (int i = 0; i < segments.length; i++) {
//       final words = segments[i].words;

//       if (words.isEmpty) {
//         continue;
//       }

//       // Baris mulai aktif ketika kata pertamanya dimulai.
//       if (words.first.startMillisecond <= positionMs) {
//         activeIndex = i;
//       } else {
//         break;
//       }
//     }

//     // Sebelum timestamp lirik pertama dimulai,
//     // tampilkan baris pertama sebagai default.
//     return activeIndex < 0 ? 0 : activeIndex;
//   }

//   // Menampilkan judul bagian lirik.
//   Widget _buildHeading() {
//     return const Padding(
//       padding: EdgeInsets.fromLTRB(20, 12, 20, 10),
//       child: Row(
//         mainAxisAlignment: MainAxisAlignment.center,
//         children: [
//           Icon(
//             Icons.graphic_eq,
//             color: Colors.white,
//             size: 22,
//           ),
//           SizedBox(width: 8),
//           Text(
//             'LYRICS',
//             style: TextStyle(
//               fontSize: 15,
//               fontWeight: FontWeight.bold,
//               letterSpacing: 3,
//               color: Colors.white,
//             ),
//           ),
//         ],
//       ),
//     );
//   }

//   // Fallback jika baris lirik tidak mempunyai daftar kata.
//   Widget _buildPlainLyric() {
//     final lyric = widget.song.lyric?.trim();

//     return Column(
//       children: [
//         _buildHeading(),
//         Expanded(
//           child: lyric == null || lyric.isEmpty
//               ? const Center(
//                   child: Text(
//                     'Lyrics are not available yet.',
//                     style: TextStyle(
//                       color: Colors.white70,
//                       fontSize: 15,
//                     ),
//                   ),
//                 )
//               : SingleChildScrollView(
//                   padding: const EdgeInsets.symmetric(
//                     horizontal: 24,
//                     vertical: 16,
//                   ),
//                   child: Text(
//                     lyric,
//                     textAlign: TextAlign.center,
//                     style: const TextStyle(
//                       fontSize: 17,
//                       height: 1.8,
//                       color: Colors.white,
//                     ),
//                   ),
//                 ),
//         ),
//         const Padding(
//           padding: EdgeInsets.fromLTRB(16, 0, 16, 12),
//           child: Text(
//             'Word synchronization requires timestamped lyrics.',
//             textAlign: TextAlign.center,
//             style: TextStyle(
//               color: Colors.white60,
//               fontSize: 11,
//             ),
//           ),
//         ),
//       ],
//     );
//   }

//   // Membuat satu baris lirik dengan highlight per kata.
//   Widget _buildLyricLine({
//     required LyricSegment segment,
//     required int index,
//     required int activeIndex,
//     required int positionMs,
//     required SongViewmodel vm,
//   }) {
//     final lineKey = _lineKeys.putIfAbsent(
//       segment.index,
//       () => GlobalKey(),
//     );

//     final isActiveSegment = index == activeIndex;

//     final spans = <InlineSpan>[];

//     for (int i = 0; i < segment.words.length; i++) {
//       final LyricWord word = segment.words[i];

//       if (i > 0) {
//         spans.add(const TextSpan(text: ' '));
//       }

//       final isActiveWord =
//           positionMs >= word.startMillisecond &&
//           positionMs < word.endMillisecond;

//       spans.add(
//         TextSpan(
//           text: word.word,
//           style: isActiveWord
//               ? const TextStyle(
//                   color: Color(0xFFFFF59D),
//                   fontWeight: FontWeight.w900,
//                   backgroundColor: Color(0xFF8D320E),
//                 )
//               : null,
//         ),
//       );
//     }

//     return Padding(
//       key: lineKey,
//       padding: const EdgeInsets.symmetric(
//         horizontal: 18,
//         vertical: 5,
//       ),
//       child: GestureDetector(
//         behavior: HitTestBehavior.opaque,

//         // Klik baris untuk mulai memainkan lagu dari baris itu.
//         onTap: segment.words.isEmpty
//             ? null
//             : () {
//                 vm.seek(
//                   Duration(
//                     milliseconds:
//                         segment.words.first.startMillisecond,
//                   ),
//                 );

//                 vm.play();
//               },

//         child: AnimatedContainer(
//           duration: const Duration(milliseconds: 200),
//           width: double.infinity,
//           padding: const EdgeInsets.symmetric(
//             horizontal: 15,
//             vertical: 13,
//           ),
//           decoration: BoxDecoration(
//             color: isActiveSegment
//                 ? Colors.white.withOpacity(0.16)
//                 : Colors.transparent,
//             borderRadius: BorderRadius.circular(16),
//           ),
//           child: segment.words.isEmpty
//               ? Text(
//                   segment.text,
//                   textAlign: TextAlign.center,
//                   style: TextStyle(
//                     fontSize: isActiveSegment ? 18 : 16,
//                     height: 1.6,
//                     fontWeight: isActiveSegment
//                         ? FontWeight.bold
//                         : FontWeight.w500,
//                     color: isActiveSegment
//                         ? Colors.white
//                         : Colors.white60,
//                   ),
//                 )
//               : Text.rich(
//                   TextSpan(
//                     children: spans,
//                   ),
//                   textAlign: TextAlign.center,
//                   style: TextStyle(
//                     fontSize: isActiveSegment ? 18 : 16,
//                     height: 1.7,
//                     fontWeight: isActiveSegment
//                         ? FontWeight.w600
//                         : FontWeight.w400,
//                     color: isActiveSegment
//                         ? Colors.white
//                         : Colors.white60,
//                   ),
//                 ),
//         ),
//       ),
//     );
//   }

//   @override
//   Widget build(BuildContext context) {
//     final vm = context.read<SongViewmodel>();
//     final segments = widget.song.lyricSegments;

//     // Jika tidak ada timestamp, tampilkan lirik mentah.
//     if (segments.isEmpty) {
//       return _buildPlainLyric();
//     }

//     return StreamBuilder<Duration>(
//       stream: vm.player.positionStream,
//       builder: (context, snapshot) {
//         // just_audio menggunakan Duration, sedangkan API
//         // mengirim timestamp dalam milidetik.
//         final positionMs = (
//           snapshot.data ?? vm.player.position
//         ).inMilliseconds;

//         final activeIndex = _findActiveSegmentIndex(
//           segments,
//           positionMs,
//         );

//         // Auto-scroll hanya saat baris aktif berubah,
//         // bukan pada setiap perubahan posisi audio.
//         if (activeIndex != _lastAutoScrollIndex) {
//           _lastAutoScrollIndex = activeIndex;

//           final songId = widget.song.id;

//           WidgetsBinding.instance.addPostFrameCallback((_) {
//             if (!mounted || widget.song.id != songId) {
//               return;
//             }

//             if (activeIndex < 0 ||
//                 activeIndex >= segments.length) {
//               return;
//             }

//             final lineContext =
//                 _lineKeys[segments[activeIndex].index]
//                     ?.currentContext;

//             if (lineContext != null) {
//               Scrollable.ensureVisible(
//                 lineContext,
//                 duration: const Duration(milliseconds: 350),
//                 curve: Curves.easeInOut,
//                 alignment: 0.45,
//               );
//             }
//           });
//         }

//         return Column(
//           children: [
//             _buildHeading(),

//             Expanded(
//               child: SingleChildScrollView(
//                 padding: const EdgeInsets.only(
//                   top: 4,
//                   bottom: 24,
//                 ),
//                 child: Column(
//                   children: [
//                     for (int i = 0; i < segments.length; i++)
//                       _buildLyricLine(
//                         segment: segments[i],
//                         index: i,
//                         activeIndex: activeIndex,
//                         positionMs: positionMs,
//                         vm: vm,
//                       ),
//                   ],
//                 ),
//               ),
//             ),
//           ],
//         );
//       },
//     );
//   }
// }