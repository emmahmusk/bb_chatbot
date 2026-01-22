import 'package:flutter/material.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';

Future<T?> pushTo<T>(
  BuildContext context,
  Widget page, {
  RouteSettings? settings,
}) async {
  return await Navigator.push<T>(
    context,
    MaterialPageRoute(
      builder: (context) => page,
      settings: settings ?? RouteSettings(name: page.toString()),
    ),
  );
}

Future<T?> pushWithAnimate<T>(
  BuildContext context,
  Widget page, {
  RouteSettings? settings,
}) {
  return Navigator.pushAndRemoveUntil<T>(
    context,
    PageRouteBuilder(
      settings: settings ?? RouteSettings(name: page.toString()),
      pageBuilder: (context, animation, secondaryAnimation) => page,
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        return FadeTransition(
          opacity: animation.drive(CurveTween(curve: Curves.easeInOut)),
          child: child,
        );
      },
      transitionDuration: const Duration(
        milliseconds: 1500,
      ),
    ),
    (route) => false,
  );
}

Future<T?> pushToWithAnimate<T>(
  BuildContext context,
  Widget page, {
  RouteSettings? settings,
}) {
  return Navigator.push<T>(
    context,
    PageRouteBuilder(
      settings: settings ?? RouteSettings(name: page.toString()),
      pageBuilder: (context, animation, secondaryAnimation) => page,
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        return FadeTransition(
          opacity: animation.drive(CurveTween(curve: Curves.easeInOut)),
          child: child,
        );
      },
      transitionDuration: const Duration(
        milliseconds: 800,
      ),
    ),
  );
}

Future<T?> popPushTo<T>(
  BuildContext context,
  Widget page, {
  RouteSettings? settings,
}) async {
  pop(context);
  return await Navigator.push<T>(
    context,
    MaterialPageRoute(
      builder: (context) => page,
      settings: settings ?? RouteSettings(name: page.toString()),
    ),
  );
}

Future<T> pushReplacementTo<T>(
  BuildContext context,
  Widget page,
) async {
  return await Navigator.pushReplacement(
    context,
    MaterialPageRoute(
      builder: (context) => page,
      settings: RouteSettings(name: page.toString()),
    ),
  );
}

Future<void> pushToAndClearStack(BuildContext context, Widget page) {
  return Navigator.of(context).pushAndRemoveUntil(
    MaterialPageRoute(
      builder: (context) => page,
      settings: RouteSettings(name: page.toString()),
    ),
    (route) => false,
  );
}

void pop<T>(BuildContext context, [T? value]) {
  return Navigator.pop<T>(context, value);
}

void popUntil(BuildContext context, Type page) {
  return Navigator.popUntil(context, ModalRoute.withName(page.toString()));
}

void popAndShowCenterDialog(BuildContext context, Widget child) {
  pop(context);
  showCenterDialog(context, child: child);
}
