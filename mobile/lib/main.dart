import 'package:flutter/material.dart';

void main() => runApp(const ChematApp());

class ChematApp extends StatelessWidget {
  const ChematApp({super.key});

  @override
  Widget build(BuildContext context) => const MaterialApp(
    home: Scaffold(
      body: SafeArea(
        child: Center(
          child: Text('CHEMa’t\nEngine milestone 1\nMultiplayer is not available yet.'),
        ),
      ),
    ),
  );
}
