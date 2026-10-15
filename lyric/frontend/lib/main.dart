import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:toko/viewmodels/song_viewmodel.dart';
import 'package:toko/views/song_view.dart';

void main() {
  runApp(MultiProvider(providers: [
    ChangeNotifierProvider(create: (_) => SongViewmodel())
  ], child: const MyApp(),));
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: SongView(),
    );
  }
}

//php artisan serve --host=0.0.0.0 --port=8000
// {'Content-Type': 'application/json'}
// http://192.168.1.245:8000
//192.168.1.245 cek dengan ipconfig di cmd
//http://10.0.2.2:8000/api khusus emulator

// void main() {
//   runApp(const MyApp());
// }

// class MyApp extends StatelessWidget {
//   const MyApp({super.key});
//
//   @override
//   Widget build(BuildContext context) {
//     return const Placeholder();
//   }
// }