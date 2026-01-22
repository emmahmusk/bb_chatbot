import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';

class Four0FourPage extends ConsumerWidget {
  const Four0FourPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Scaffold(
      backgroundColor: colors.primary,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Image.asset(
              Pngs.four0four,
              width: 170,
              height: 170,
              fit: BoxFit.cover,
            ),
            const SizedBox(height: 10),
            Text(
              'Page not found',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: colors.alwaysWhite,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              'We couldn’t find the page you are looking for',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: colors.always8B949E,
              ),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: 91,
              child: CustomOutlinedButton.big(
                text: 'Go home',
                onTap: () {
                  context.go(DashboardRoutes.trending);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
