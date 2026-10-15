import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:provider/provider.dart';
import 'package:toko/models/lyric_segment.dart';
import 'package:toko/models/lyric_word.dart';
import 'package:toko/models/song.dart';
import 'package:toko/viewmodels/song_viewmodel.dart';

//MINIPLAYER
class PlayerView extends StatelessWidget {
  const PlayerView({super.key});

  @override
  Widget build(BuildContext context) {
    final songVM = Provider.of<SongViewmodel>(context);

    return songVM.currentSong == null
        ? const SizedBox()
        : GestureDetector(
            onTap: () {
              showModalBottomSheet(
                context: context,
                isScrollControlled: true,
                backgroundColor: Colors.transparent,
                builder: (_) => FullPlayer(
                  onClose: () => Navigator.pop(context),
                ),
              );
            },
            child: const _MiniPlayerContainer(),
          );
  }
}

class _MiniPlayerContainer extends StatelessWidget {
  const _MiniPlayerContainer();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 95,
      margin: const EdgeInsets.all(12),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Colors.orange.shade600.withOpacity(.95),
            Colors.orange.shade400.withOpacity(.95),
          ],
        ),
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: Colors.orange.shade300.withOpacity(.5),
            blurRadius: 18,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: const Row(
        children: [
          _MiniArtwork(),
          SizedBox(width: 14),
          Expanded(child: _MiniInfo()),
          SizedBox(width: 12),
          _MiniControlButton(),
        ],
      ),
    );
  }
}

class _MiniArtwork extends StatelessWidget {
  const _MiniArtwork();

  @override
  Widget build(BuildContext context) {
    final song =
        context.select<SongViewmodel, Song?>((vm) => vm.currentSong);

    return RepaintBoundary(
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: song?.thumbnailPath != null
            ? Image.network(
                "http://10.0.2.2:9000/songs/${song!.thumbnailPath}",
                width: 62,
                height: 62,
                fit: BoxFit.cover,
                gaplessPlayback: true,
                filterQuality: FilterQuality.low,
              )
            : const Icon(Icons.music_note, size: 62),
      ),
    );
  }
}

class _MiniInfo extends StatelessWidget {
  const _MiniInfo();

  @override
  Widget build(BuildContext context) {
    final songVM = Provider.of<SongViewmodel>(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          songVM.currentSong?.title ?? "Unknown",
          style: const TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        if (songVM.currentSong?.artisName != null) ...[
          const SizedBox(height: 4),
          Text(
            songVM.currentSong!.artisName,
            style: const TextStyle(
              fontSize: 13,
              color: Colors.white70,
            ),
          ),
        ],
        const SizedBox(height: 8),
        const _MiniProgress(),
      ],
    );
  }
}

class _MiniProgress extends StatelessWidget {
  const _MiniProgress();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<SongViewmodel>();

    return StreamBuilder<Duration?>(
      stream: vm.player.durationStream,
      builder: (context, snapshot) {
        final duration = snapshot.data ?? Duration.zero;
        return StreamBuilder<Duration>(
          stream: vm.player.positionStream,
          builder: (context, snapshot) {
            final position = snapshot.data ?? Duration.zero;
            final progress = duration.inMilliseconds == 0
                ? 0.0
                : (position.inMilliseconds / duration.inMilliseconds)
                    .clamp(0.0, 1.0);
            return ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 4,
                color: Colors.white,
                backgroundColor: Colors.white30,
              ),
            );
          },
        );
      },
    );
  }
}

class _MiniControlButton extends StatelessWidget {
  const _MiniControlButton();

  @override
  Widget build(BuildContext context) {
    final vm = context.read<SongViewmodel>();

    return StreamBuilder<bool>(
      stream: vm.player.playingStream,
      builder: (context, snapshot) {
        final isPlaying = snapshot.data ?? false;
        return IconButton(
          onPressed: () => isPlaying ? vm.pause() : vm.play(),
          icon: Icon(
            isPlaying ? Icons.pause_circle_filled : Icons.play_circle_fill,
            color: Colors.white,
            size: 42,
          ),
        );
      },
    );
  }
}

//FULLPLAYER
class FullPlayer extends StatefulWidget {
  final VoidCallback onClose;

  const FullPlayer({super.key, required this.onClose});

  @override
  State<FullPlayer> createState() => _FullPlayerState();
}

class _FullPlayerState extends State<FullPlayer> {
  bool _showLyrics = false;

  void _toggleLyrics() => setState(() => _showLyrics = !_showLyrics);

  @override
  Widget build(BuildContext context) {
    return FractionallySizedBox(
      heightFactor: 0.95,
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFFFFA726), Color(0xFFFF7043)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
          borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
        ),
        child: SafeArea(
          child: Column(
            children: [
              _PlayerHeader(
                onClose: widget.onClose,
                showLyrics: _showLyrics,
                onToggleLyrics: _toggleLyrics,
              ),
              Expanded(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 300),
                  child: _showLyrics
                      ? const _LyricsPanel(key: ValueKey('lyrics'))
                      : _PlayerArtwork(
                          key: const ValueKey('artwork'),
                          onTap: _toggleLyrics,
                        ),
                ),
              ),
              const _PlayerInfo(),
              const _PlayerProgress(),
              const _PlayerControls(),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}

class _PlayerHeader extends StatelessWidget {
  final VoidCallback onClose;
  final VoidCallback onToggleLyrics;
  final bool showLyrics;

  const _PlayerHeader({
    required this.onClose,
    required this.onToggleLyrics,
    required this.showLyrics,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 5,
            decoration: BoxDecoration(
              color: Colors.white38,
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          const Spacer(),
          IconButton(
            onPressed: onToggleLyrics,
            tooltip: showLyrics ? 'Tampilkan cover' : 'Tampilkan lirik',
            icon: Icon(
              showLyrics ? Icons.album_outlined : Icons.lyrics_outlined,
              color: Colors.white,
            ),
          ),
          IconButton(
            onPressed: onClose,
            icon: const Icon(Icons.close, color: Colors.white),
          ),
        ],
      ),
    );
  }
}

class _PlayerArtwork extends StatelessWidget {
  final VoidCallback onTap;

  const _PlayerArtwork({super.key, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final song =
        context.select<SongViewmodel, Song?>((vm) => vm.currentSong);

    final size = MediaQuery.of(context).size.width * 0.75;

    return RepaintBoundary(
      child: Center(
        child: GestureDetector(
          onTap: onTap,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: song?.thumbnailPath != null
                ? Image.network(
                    "http://10.0.2.2:9000/songs/${song!.thumbnailPath}",
                    width: size,
                    height: size,
                    fit: BoxFit.cover,
                    gaplessPlayback: true,
                    filterQuality: FilterQuality.low,
                  )
                : Container(
                    width: size,
                    height: size,
                    color: Colors.black26,
                    child: const Icon(
                      Icons.music_note,
                      size: 80,
                      color: Colors.white,
                    ),
                  ),
          ),
        ),
      ),
    );
  }
}

//LYRICS
const _lyricTextStyle = TextStyle(
  fontSize: 24,
  height: 1.3,
  fontWeight: FontWeight.bold,
);

class _LyricsPanel extends StatelessWidget {
  const _LyricsPanel({super.key});

  @override
  Widget build(BuildContext context) {
    final song =
        context.select<SongViewmodel, Song?>((vm) => vm.currentSong);

    if (song == null) return const SizedBox();

    // Lirik tersinkron (per baris & per kata)
    if (song.lyricSegments.isNotEmpty) {
      // key berdasarkan id lagu: state di-reset otomatis saat lagu berganti
      return _SyncedLyrics(
        key: ValueKey(song.id),
        segments: song.lyricSegments,
      );
    }

    // Fallback: lirik teks biasa tanpa timestamp
    final plain = song.lyric?.trim() ?? '';
    if (plain.isEmpty) {
      return const Center(
        child: Text(
          'Lirik belum tersedia',
          style: TextStyle(color: Colors.white70, fontSize: 16),
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
      child: Text(
        plain,
        style: _lyricTextStyle.copyWith(
          fontSize: 18,
          color: Colors.white.withOpacity(.9),
        ),
      ),
    );
  }
}

class _SyncedLyrics extends StatefulWidget {
  final List<LyricSegment> segments;

  const _SyncedLyrics({super.key, required this.segments});

  @override
  State<_SyncedLyrics> createState() => _SyncedLyricsState();
}

class _SyncedLyricsState extends State<_SyncedLyrics>
    with SingleTickerProviderStateMixin {
  late final SongViewmodel _vm;
  late final List<GlobalKey> _keys;
  late final Ticker _ticker;
  Timer? _resumeTimer;

  /// Posisi lagu (ms), diperbarui tiap frame oleh ticker.
  /// ValueNotifier hanya memberi tahu listener jika nilainya berubah,
  /// jadi saat lagu di-pause tidak ada rebuild sama sekali.
  final ValueNotifier<int> _posMs = ValueNotifier<int>(0);

  int _activeIndex = -1;
  bool _userDragging = false;

  @override
  void initState() {
    super.initState();
    _vm = context.read<SongViewmodel>();
    _keys = List.generate(widget.segments.length, (_) => GlobalKey());

    final ms = _vm.player.position.inMilliseconds;
    _posMs.value = ms;
    _activeIndex = _indexAt(ms);

    // Satu sumber posisi untuk semua baris: dibaca tiap frame (~60fps),
    // tidak bergantung pada interval positionStream (maks 200 ms).
    _ticker = createTicker(_onTick)..start();

    // Langsung lompat ke baris yang sedang dinyanyikan saat panel dibuka
    WidgetsBinding.instance
        .addPostFrameCallback((_) => _scrollToActive(animate: false));
  }

  @override
  void dispose() {
    _ticker.dispose();
    _posMs.dispose();
    _resumeTimer?.cancel();
    super.dispose();
  }

  /// Baris aktif = baris terakhir yang start_ms-nya sudah terlewati.
  int _indexAt(int ms) {
    var result = -1;
    for (var i = 0; i < widget.segments.length; i++) {
      if (widget.segments[i].startMillisecond <= ms) {
        result = i;
      } else {
        break;
      }
    }
    return result;
  }

  void _onTick(Duration _) {
    final ms = _vm.player.position.inMilliseconds;
    _posMs.value = ms;

    final index = _indexAt(ms);
    if (index == _activeIndex) return;

    setState(() => _activeIndex = index);
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToActive());
  }

  void _scrollToActive({bool animate = true}) {
    if (!mounted || _userDragging || _activeIndex < 0) return;

    final ctx = _keys[_activeIndex].currentContext;
    if (ctx == null) return;

    Scrollable.ensureVisible(
      ctx,
      alignment: 0.35,
      duration: animate ? const Duration(milliseconds: 450) : Duration.zero,
      curve: Curves.easeOutCubic,
    );
  }

  /// Hentikan auto-scroll saat user menggeser lirik sendiri,
  /// lanjutkan 2 detik setelah user berhenti.
  bool _onScroll(ScrollNotification n) {
    if (n is ScrollStartNotification && n.dragDetails != null) {
      _resumeTimer?.cancel();
      _userDragging = true;
    } else if (n is ScrollEndNotification && _userDragging) {
      _resumeTimer?.cancel();
      _resumeTimer = Timer(const Duration(seconds: 2), () {
        _userDragging = false;
        _scrollToActive();
      });
    }
    return false;
  }

  void _seekTo(LyricSegment segment) {
    _userDragging = false;
    _vm.seek(Duration(milliseconds: segment.startMillisecond));
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final h = constraints.maxHeight;

        return NotificationListener<ScrollNotification>(
          onNotification: _onScroll,
          child: SingleChildScrollView(
            physics: const BouncingScrollPhysics(),
            // Padding atas/bawah supaya baris pertama & terakhir bisa
            // tetap di-scroll ke posisi aktif.
            padding: EdgeInsets.fromLTRB(28, h * 0.35, 28, h * 0.55),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var i = 0; i < widget.segments.length; i++)
                  _LyricLine(
                    key: _keys[i],
                    segment: widget.segments[i],
                    isActive: i == _activeIndex,
                    position: _posMs,
                    onTap: () => _seekTo(widget.segments[i]),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _LyricLine extends StatelessWidget {
  final LyricSegment segment;
  final bool isActive;
  final ValueListenable<int> position;
  final VoidCallback onTap;

  const _LyricLine({
    super.key,
    required this.segment,
    required this.isActive,
    required this.position,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final Widget text;

    if (isActive && segment.words.isNotEmpty) {
      text = _ActiveLyricText(segment: segment, position: position);
    } else {
      text = Text(
        segment.text,
        style: _lyricTextStyle.copyWith(
          color: Colors.white.withOpacity(isActive ? 1 : .4),
        ),
      );
    }

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: text,
      ),
    );
  }
}

/// Baris yang sedang aktif: kata di-highlight satu per satu mengikuti posisi lagu.
/// Hanya widget ini yang rebuild tiap perubahan posisi, baris lain tetap statis.
/// Posisi datang dari ValueNotifier milik parent (bukan stream baru),
/// jadi tidak ada subscribe ulang saat pindah segmen.
class _ActiveLyricText extends StatelessWidget {
  final LyricSegment segment;
  final ValueListenable<int> position;

  const _ActiveLyricText({required this.segment, required this.position});

  @override
  Widget build(BuildContext context) {
    final words = segment.words;

    return ValueListenableBuilder<int>(
      valueListenable: position,
      builder: (context, ms, _) {
        return Text.rich(
          TextSpan(
            style: _lyricTextStyle,
            children: [
              for (var i = 0; i < words.length; i++)
                TextSpan(
                  text: i < words.length - 1
                      ? '${words[i].word} '
                      : words[i].word,
                  style: TextStyle(
                    color: Colors.white
                        .withOpacity(_wordOpacity(words[i], ms)),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}

/// Kata memudar dari redup ke terang selama durasinya, jadi transisinya halus.
/// Untuk highlight langsung tanpa fade, ganti isinya dengan:
/// `return ms >= w.startMillisecond ? 1.0 : .65;`
double _wordOpacity(LyricWord w, int ms) {
  const dim = .65;
  final len = w.endMillisecond - w.startMillisecond;
  final t = len <= 0
      ? (ms >= w.startMillisecond ? 1.0 : 0.0)
      : ((ms - w.startMillisecond) / len).clamp(0.0, 1.0).toDouble();
  return dim + (1 - dim) * t;
}

class _PlayerInfo extends StatelessWidget {
  const _PlayerInfo();

  @override
  Widget build(BuildContext context) {
    final song = context.watch<SongViewmodel>();

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Column(
        children: [
          Text(
            song.currentSong?.title ?? "Unknown",
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 6),
          Text(
            song.currentSong?.artisName ?? "Unknown Artist",
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 15,
            ),
          ),
        ],
      ),
    );
  }
}

class _PlayerProgress extends StatefulWidget {
  const _PlayerProgress();

  @override
  State<_PlayerProgress> createState() => _PlayerProgressState();
}

class _PlayerProgressState extends State<_PlayerProgress> {
  double? _dragValue;

  String _format(Duration d) {
    final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return "$m:$s";
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<SongViewmodel>();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 22),
      child: StreamBuilder<Duration?>(
        stream: vm.player.durationStream,
        builder: (context, snapshot) {
          final duration = snapshot.data ?? Duration.zero;
          final max = duration.inMilliseconds.toDouble();

          return StreamBuilder<Duration>(
            stream: vm.player.positionStream,
            builder: (context, snapshot) {
              final position = snapshot.data ?? Duration.zero;
              return Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(_format(position),
                          style: const TextStyle(color: Colors.white70)),
                      Text(_format(duration),
                          style: const TextStyle(color: Colors.white70)),
                    ],
                  ),
                  Slider(
                    min: 0,
                    max: max,
                    // _dragValue dipakai supaya thumb ikut bergeser saat di-drag
                    value: (_dragValue ?? position.inMilliseconds.toDouble())
                        .clamp(0.0, max)
                        .toDouble(),
                    activeColor: Colors.white,
                    inactiveColor: Colors.white38,
                    onChanged: (value) {
                      setState(() => _dragValue = value);
                    },
                    onChangeEnd: (value) {
                      vm.seek(Duration(milliseconds: value.toInt()));
                      setState(() => _dragValue = null);
                    },
                  )
                ],
              );
            },
          );
        },
      ),
    );
  }
}

class _PlayerControls extends StatelessWidget {
  const _PlayerControls();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<SongViewmodel>();

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        IconButton(
          onPressed: vm.skipToPrevious,
          icon: const Icon(Icons.skip_previous, size: 38, color: Colors.white),
        ),
        const SizedBox(width: 20),
        StreamBuilder<bool>(
          stream: vm.player.playingStream,
          builder: (context, snapshot) {
            final isPlaying = snapshot.data ?? false;
            return GestureDetector(
              onTap: () => isPlaying ? vm.pause() : vm.play(),
              child: Icon(
                isPlaying ? Icons.pause_circle : Icons.play_circle_fill,
                size: 70,
                color: Colors.white,
              ),
            );
          },
        ),
        const SizedBox(width: 20),
        IconButton(
          onPressed: vm.skipToNext,
          icon: const Icon(Icons.skip_next, size: 38, color: Colors.white),
        ),
      ],
    );
  }
}