import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:toko/models/song.dart';
import 'package:toko/viewmodels/song_viewmodel.dart';
import 'package:toko/views/player_view.dart';

class SongView extends StatefulWidget {
  const SongView({super.key});

  @override
  State<SongView> createState() => _SongViewState();
}

class _SongViewState extends State<SongView> {
  @override
  void initState() {
    super.initState();
    Future.microtask((){
      final songVM = Provider.of<SongViewmodel>(context, listen: false);
      songVM.fetchSong();
    });
  }

  @override
  Widget build(BuildContext context) {
    final songViewmodel = Provider.of<SongViewmodel>(context);
    return Scaffold(
      backgroundColor: Colors.orange.shade50,
      body: songViewmodel.isLoading
          ? const Center(child: CircularProgressIndicator.adaptive())
          : RefreshIndicator(
              color: Colors.orange,
              onRefresh: () async {},
              child: SafeArea(
                child: CustomScrollView(
                  slivers: [
                    SliverToBoxAdapter(child: _buildHeader(context)),
                    SliverToBoxAdapter(child: const SizedBox(height: 18)),
                    SliverToBoxAdapter(child: _buildQuickActions()),
                    SliverToBoxAdapter(child: const SizedBox(height: 18)),
                    SliverToBoxAdapter(child: _buildSectionTitle("Recently Played")),
                    SliverToBoxAdapter(child: const SizedBox(height: 8)),
                    SliverToBoxAdapter(child: _buildRecentlyPlayed()),
                    SliverToBoxAdapter(child: const SizedBox(height: 18)),
                    SliverToBoxAdapter(child: _buildSectionTitle("Popular Now")),
                    SliverToBoxAdapter(child: const SizedBox(height: 8)),
                    SliverToBoxAdapter(child: _buildPopularList()),
                    SliverToBoxAdapter(child: const SizedBox(height: 120)),
                  ],
                ),
              ),
            ),
      // mini player
      bottomSheet: songViewmodel.currentSong != null
      ? PlayerView()
      : SizedBox()
    );
  }

  Widget _buildHeader(BuildContext context) {
    return UserHeader();
  }

  Widget _buildQuickActions() {
    final actions = [
      {"icon": Icons.favorite, "label": "Favorites", "onTap": () {}},
      {"icon": Icons.queue_music, "label": "Playlists", "onTap": () {}},
      {"icon": Icons.upload_file, "label": "Upload", "onTap": () {}},
      {"icon": Icons.settings, "label": "Settings", "onTap": () {}},
    ];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 12),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Colors.orange.shade700,
              Colors.orange.shade500,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: Colors.orange.shade200.withOpacity(0.7),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: actions.map((a) {
            return InkWell(
              onTap: a["onTap"] as void Function()?,
              borderRadius: BorderRadius.circular(16),
              splashColor: Colors.white.withOpacity(0.2),
              highlightColor: Colors.white.withOpacity(0.1),
              child: Column(
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Colors.white.withOpacity(0.9),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.1),
                          blurRadius: 6,
                          offset: const Offset(0, 3),
                        ),
                      ],
                    ),
                    child: Icon(
                      a["icon"] as IconData,
                      size: 24,
                      color: Colors.orange.shade700,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    a["label"] as String,
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // TITLE
          Text(
            title,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.orange.shade800,
              letterSpacing: 0.5,
            ),
          ),

          // SEE ALL
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.orange.shade50,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.orange.shade300, width: 1),
            ),
            child: InkWell(
              onTap: (){},
              child: Text(
              "See All",
                style: TextStyle(
                  color: Colors.orange.shade700,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            )
          )
        ],
      ),
    );
  }

  Widget _buildRecentlyPlayed() {
    final recentlyPlayed = context.select<SongViewmodel, List<Song>>(  (vm) => vm.recentlyPlayed);

    final songList = context.select<SongViewmodel, List<Song>>( (vm) => vm.songList);

    final songViewmodel = context.read<SongViewmodel>();

    if (recentlyPlayed.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Container(
          height: 100,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                Colors.orange.shade400,
                Colors.orange.shade300,
              ],
            ),
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.orange.shade200.withOpacity(0.5),
                blurRadius: 10,
                offset: const Offset(0, 4),
              )
            ],
          ),
          child: const Center(
            child: Text(
              "Belum ada riwayat putar.",
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      );
    }

    /// 🔥 O(1) index lookup
    final Map<int, int> indexMap = {
      for (int i = 0; i < songList.length; i++)
        songList[i].id!: i
    };

    return SizedBox(
      height: 130,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        scrollDirection: Axis.horizontal,
        cacheExtent: 300,
        physics: const BouncingScrollPhysics(),
        itemCount: recentlyPlayed.length,
        separatorBuilder: (_, __) =>
            const SizedBox(width: 12),
        itemBuilder: (context, i) {
          final s = recentlyPlayed[i];

          return RepaintBoundary(
            child: GestureDetector(
              onTap: () async {
                await songViewmodel.playSong(s);
              },
              child: Container(
                width: 240,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Colors.orange.shade700,
                      Colors.orange.shade500,
                    ],
                  ),
                  borderRadius: BorderRadius.circular(18),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.orange.shade300
                          .withOpacity(0.6),
                      blurRadius: 10,
                      offset: const Offset(0, 5),
                    )
                  ],
                ),
                child: Row(
                  children: [

                    /// Album Art
                    ClipRRect(
                      borderRadius:
                          BorderRadius.circular(12),
                      child: Image.network(
                        "http://10.0.2.2:9000/songs/${s.thumbnailPath}",
                        width: 72,
                        height: 72,
                        fit: BoxFit.cover,
                        gaplessPlayback: true,
                        filterQuality:
                            FilterQuality.low,
                        errorBuilder: (_, __, ___) =>
                            const Icon(
                          Icons.music_note,
                          size: 72,
                        ),
                      )
                    ),

                    const SizedBox(width: 12),

                    /// Title + Artist
                    Expanded(
                      child: Column(
                        crossAxisAlignment:
                            CrossAxisAlignment.start,
                        mainAxisAlignment:
                            MainAxisAlignment.center,
                        children: [
                          Text(
                            s.title,
                            maxLines: 2,
                            overflow:
                                TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontWeight:
                                  FontWeight.bold,
                              fontSize: 14,
                              color: Colors.white,
                            ),
                          ),
                          Text(
                            s.artisName,
                            overflow:
                                TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.white
                                  .withOpacity(0.9),
                            ),
                          ),
                        ],
                      ),
                    ),

                    IconButton(
                      onPressed: () {},
                      icon: const Icon(
                        Icons.queue_music,
                        size: 28,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildPopularList() {
    final songViewmodel = Provider.of<SongViewmodel>(context);
    final songList = songViewmodel.songList;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: GridView.builder(
        physics: const NeverScrollableScrollPhysics(), // jika di dalam ScrollView utama
        shrinkWrap: true,
        itemCount: songList.length,
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          mainAxisSpacing: 14,
          crossAxisSpacing: 14,
          childAspectRatio: 0.75,
        ),
        itemBuilder: (context, index) {
          final s = songList[index];
          return GestureDetector(
            onTap: () async {
              await songViewmodel.playSong(s);
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 250),
              curve: Curves.easeOut,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.white,
                    Colors.orange.withOpacity(0.08),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.orange.withOpacity(0.15),
                    blurRadius: 12,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ClipRRect(
                    borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                    child: Image.network(
                      "http://10.0.2.2:9000/songs/${s.thumbnailPath}",
                      width: double.infinity,
                      height: 120, // <--- batasi tinggi
                      fit: BoxFit.cover,
                    )
                  ),
                  Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          s.title,
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                s.artisName,
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.grey.shade600,
                                  fontWeight: FontWeight.w500,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 4),
                            GestureDetector(
                              onTap: () {},
                              child: const Padding(
                                padding: EdgeInsets.all(4),
                                child: Icon(
                                  Icons.queue_music,
                                  size: 18,
                                ),
                              ),
                            ),
                          ],
                        )
                      ],
                    ),
                  )
                ],
              )
            ),
          );
        },
      ),
    );
  }
}

class UserHeader extends StatelessWidget {
  const UserHeader({super.key});

  @override
  Widget build(BuildContext context) {
    return const _HeaderContainer();
  }
}

class _HeaderContainer extends StatelessWidget {
  const _HeaderContainer();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Colors.orange.shade700,
            Colors.orange.shade400,
          ],
        ),
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: Colors.orange.withOpacity(.35),
            blurRadius: 14,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: const Row(
        children: [
          ProfileAvatar(),
          SizedBox(width: 18),
          Expanded(child: _UserInfo()),
          _LogoutButton(),
        ],
      ),
    );
  }
}

class ProfileAvatar extends StatelessWidget {
  const ProfileAvatar({super.key});

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: Container(
        padding: const EdgeInsets.all(3),
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(
            colors: [
              Colors.white,
              Colors.orange.shade200,
            ],
          ),
        ),
        child: CircleAvatar(
          radius: 36,
          backgroundColor: Colors.white,
          child: ClipOval(
            child: Icon(
              Icons.person,
              size: 36,
              color: Colors.orange.shade700,
            )
          ),
        ),
      ),
    );
  }
}

class _UserInfo extends StatelessWidget {
  const _UserInfo();

  @override
  Widget build(BuildContext context) {

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          "Selamat datang",
          style: TextStyle(
            color: Colors.white.withOpacity(.9),
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          "Arsal",
          style: const TextStyle(
            color: Colors.white,
            fontSize: 22,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        _PlayStat(playedCount: 1000),
      ],
    );
  }
}

class _PlayStat extends StatelessWidget {
  const _PlayStat({required this.playedCount});

  final int playedCount;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding:
          const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(.15),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.play_arrow,
              size: 16, color: Colors.white),
          const SizedBox(width: 6),
          Text(
            "$playedCount Plays",
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _LogoutButton extends StatelessWidget {
  const _LogoutButton();

  @override
  Widget build(BuildContext context) {
    return IconButton(
      onPressed: () {
        // logout logic
      },
      icon: const Icon(
        Icons.person,
        color: Colors.white,
      ),
    );
  }
}