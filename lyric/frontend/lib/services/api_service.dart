import 'package:dio/dio.dart';
import 'package:toko/models/song.dart';

class ApiService {
  final dio = Dio(BaseOptions(
    baseUrl: "http://10.0.2.2:8000/api",
    sendTimeout: Duration(seconds: 60),
    receiveTimeout: Duration(seconds: 60)
  ));

  Future<List<Song>> getAllSong()async{
    try{
      final response = await dio.get("/song");
      return(response.data['data'] as List).map((item) => Song.fromJson(item)).toList();
    }on DioException catch(e){
      throw Exception(e.response);
    }
  }

  Future<Map<String, dynamic>> uploadSong(String title, String artisName, String thumbnailPath, String songPath, String? language)async{
    try{
      final thumbnailFile = await MultipartFile.fromFile(thumbnailPath);
      final songFile = await MultipartFile.fromFile(songPath);
      final request = FormData.fromMap({
        "title": title,
        "artis_name": artisName,
        "thumbnail_file": thumbnailFile,
        "song_file": songFile,
        "language": language
      });
      final response = await dio.post("/song", data: request);
      return response.data;
    }on DioException catch(e){
      return{
        "success": false,
        "message": e.response?.data['message'].toString() ?? "Terjadi kesalahan"
      };
    }
  }
}