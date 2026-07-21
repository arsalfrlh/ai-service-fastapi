import 'package:dio/dio.dart';
import 'package:toko/models/message.dart';

class ApiService {
  final dio = Dio(BaseOptions(
    baseUrl: "http://127.0.0.1:8000",
    sendTimeout: Duration(seconds: 300),
    connectTimeout: Duration(seconds: 300),
    receiveTimeout: Duration(seconds: 300)
  ));

  Future<List<Message>> getAllMessage()async{
    try{
      final response = await dio.get("/message");
      return (response.data['data'] as List).map((item) => Message.fromJson(item)).toList();
    }on DioException catch(e){
      throw Exception(e.response);
    }
  }

  Future<void> sendMessage(String message, List<String> imagePaths)async{
    List<MultipartFile> imageFiles = [];
    if(imagePaths.isNotEmpty){
      for(var image in imagePaths){
        imageFiles.add(await MultipartFile.fromFile(image));
      }
    }

    try{
      final request = FormData.fromMap({
        "question": message,
        if(imagePaths.isNotEmpty)
        "images": imageFiles
      });
      await dio.post("/message", data: request);
    }on DioException catch(e){
      throw Exception(e.response);
    }
  }
}