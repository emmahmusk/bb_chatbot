import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class TimelineBreakdown extends ConsumerWidget {
  const TimelineBreakdown({
    super.key,
    required this.events,
  });

  final List<TimelineEvent> events;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (int i = 0; i < events.length; i++)
          TimelineItem(
            event: events[i],
            isLast: i == events.length - 1,
          ),
      ],
    );
  }
}

class TimelineItem extends ConsumerWidget {
  const TimelineItem({
    super.key,
    required this.event,
    required this.isLast,
  });

  final TimelineEvent event;
  final bool isLast;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 24,
            child: Column(
              children: [
                Container(
                  width: 16,
                  height: 16,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: event.isCompleted ? null : colors.always8B949E,
                  ),
                  child: event.isCompleted
                      ? Image.asset(
                          Pngs.checkCircle,
                          width: 16,
                          height: 16,
                        )
                      : Container(
                          width: 8,
                          height: 8,
                          margin: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: colors.alwaysWhite,
                          ),
                        ),
                ),
                // Connecting line
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 1,
                      margin: const EdgeInsets.only(top: 4, bottom: 4),
                      color: event.isCompleted
                          ? colors.always27D07F
                          : colors.always8B949E,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          // Content column
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(
                bottom: isLast ? 0 : 32,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    event.title,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                      color: colors.alwaysWhite,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    event.timestamp,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w400,
                      color: colors.always8B949E,
                    ),
                  ),
                  if (event.description != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      event.description!,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w400,
                        color: colors.always8B949E,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class TimelineEvent {
  const TimelineEvent({
    required this.title,
    required this.timestamp,
    required this.isCompleted,
    this.description,
  });

  final String title;
  final String timestamp;
  final bool isCompleted;
  final String? description;
}
