import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/extensions/list_extension.dart';
import 'package:frontend/app/shared/presentation/widgets/app_logo.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/app/shared/presentation/widgets/table/custom_table_row.dart';
import 'package:frontend/app/shared/presentation/widgets/table/table_header.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class CustomTable extends ConsumerWidget {
  final ValueChanged<int>? onTap;
  final Widget? leading;
  final List<String> headers;
  final List<List<String>> data;
  final bool isCurved;
  final EdgeInsets? margin;

  final bool paginate;
  final int rowsPerPage;
  final ValueChanged<int>? onPrevious;
  final Function(int nextPage, bool requiresRequest)? onNext;
  final int currentPage;
  final bool isLoadingMore;

  final Widget Function(
    String value,
    Widget old,
    int columnIndex,
    int rowIndex,
  )? cellDecorator;
  const CustomTable({
    super.key,
    required this.headers,
    required this.data,
    this.onTap,
    this.leading,
    this.isCurved = false,
    this.cellDecorator,
    this.margin,
    this.paginate = true,
    this.rowsPerPage = 10,
    this.onPrevious,
    this.onNext,
    this.currentPage = 1,
    this.isLoadingMore = false,
  });

  List<List<List<String>>> chunkData() {
    final List<List<List<String>>> chunks = [];
    for (int i = 0; i < data.length; i += rowsPerPage) {
      final endIndex =
          (i + rowsPerPage) > data.length ? data.length : (i + rowsPerPage);
      chunks.add(data.sublist(i, endIndex));
    }
    return chunks;
  }

  int get totalPages => (data.length / rowsPerPage).ceil();

  List<int> genPageNumbers(int currentPage) {
    const int maxPages = 5;
    if (totalPages <= maxPages) {
      return List.generate(totalPages, (index) => index + 1);
    }
    if (currentPage <= 3) {
      return [1, 2, 3, 4, -1, totalPages];
    } else if (currentPage > totalPages - 3) {
      return [
        1,
        -1,
        totalPages - 3,
        totalPages - 2,
        totalPages - 1,
        totalPages
      ];
    } else {
      return [
        1,
        -1,
        currentPage - 1,
        currentPage,
        currentPage + 1,
        -1,
        totalPages
      ];
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    List<List<String>> dataToDisplay = data;
    if (paginate && data.length > rowsPerPage) {
      final chunks = chunkData();
      dataToDisplay = chunks[currentPage - 1];
    }

    final canGoBack = currentPage > 1;
    final isEmpty = data.isEmpty;
    return Container(
      margin: margin ?? const EdgeInsets.symmetric(horizontal: 32),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Container(
          decoration: BoxDecoration(
            color: colors.alwaysWhite,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: colors.alwaysE6E9F1),
          ),
          child: Column(
            children: [
              if (leading != null) ...[
                Container(
                  padding: const EdgeInsets.symmetric(
                    vertical: 15,
                    horizontal: 24,
                  ),
                  child: leading,
                ),
                const CustomDivider(),
              ],
              TableHeader(
                tabs: headers,
                isCurved: isCurved,
              ),
              const CustomDivider(),
              Expanded(
                child: Builder(
                  builder: (context) {
                    if (isEmpty) {
                      return Center(
                        child: Text(
                          "No data to display",
                          style: TextStyle(
                            color: colors.alwaysBlack,
                            fontSize: 16,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      );
                    }
                    return ListView(
                      children: [
                        for (final (rowIndex, list)
                            in dataToDisplay.enumerate())
                          Builder(
                            builder: (context) {
                              final row = Container(
                                color: colors.transparent,
                                child: CustomTableRow(
                                  data: list,
                                  rowIndex: rowIndex,
                                  cellDecorator: cellDecorator,
                                ),
                              );
                              if (onTap == null) return row;

                              return Clickable(
                                onClick: () {
                                  final actualIndex =
                                      (currentPage - 1) * rowsPerPage +
                                          rowIndex;
                                  onTap?.call(actualIndex);
                                },
                                child: row,
                              );
                            },
                          ),
                      ],
                    );
                  },
                ),
              ),
              if (paginate && !isEmpty) ...[
                const CustomDivider(),
                Container(
                  padding: const EdgeInsets.symmetric(
                    vertical: 15,
                    horizontal: 24,
                  ),
                  child: Builder(
                    builder: (context) {
                      if (isLoadingMore) {
                        return AppLogo(
                          color: colors.primary,
                          size: 40,
                          shouldAnimate: true,
                        );
                      }
                      return Row(
                        children: [
                          IgnorePointer(
                            ignoring: !canGoBack,
                            child: Opacity(
                              opacity: canGoBack ? 1 : 0,
                              child: CustomOutlinedButtonWithIcon(
                                text: "Previous",
                                color: colors.alwaysBlack,
                                onTap: () {
                                  onPrevious?.call(currentPage - 1);
                                },
                                icon: Icon(
                                  Icons.arrow_back_rounded,
                                  size: 16,
                                  color: colors.alwaysBlack,
                                ),
                              ),
                            ),
                          ),
                          const Spacer(),
                          Row(
                            children: [
                              for (final page in genPageNumbers(currentPage))
                                if (page == -1)
                                  const Text("...")
                                else
                                  Clickable(
                                    onClick: () {
                                      if (page != currentPage) {
                                        onNext?.call(page, false);
                                      }
                                    },
                                    child: Container(
                                      width: 40,
                                      height: 40,
                                      decoration: BoxDecoration(
                                        borderRadius: BorderRadius.circular(8),
                                        color: page == currentPage
                                            ? colors.alwaysF0F2F5
                                            : colors.transparent,
                                      ),
                                      child: Center(
                                        child: Text(
                                          "$page",
                                          style: TextStyle(
                                            fontSize: 12,
                                            color: colors.alwaysBlack,
                                            fontWeight: FontWeight.w500,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                            ],
                          ),
                          const Spacer(),
                          CustomOutlinedButtonWithIcon(
                            text: "Next",
                            color: colors.alwaysBlack,
                            onTap: () {
                              final nextChunkIndex = currentPage;
                              final requiresRequest =
                                  nextChunkIndex >= chunkData().length;
                              onNext?.call(currentPage + 1, requiresRequest);
                            },
                            iconPosition: IconPosition.right,
                            icon: Transform.translate(
                              offset: const Offset(12, 0),
                              child: Icon(
                                Icons.arrow_forward_rounded,
                                size: 16,
                                color: colors.alwaysBlack,
                              ),
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ),
              ]
            ],
          ),
        ),
      ),
    );
  }
}
