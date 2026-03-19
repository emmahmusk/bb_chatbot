import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/competition/data/models/competition_models.dart';
import 'package:frontend/app/modules/competition/domain/repositories/competition_repository.dart';
import 'package:frontend/app/shared/extensions/context_extension.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class CompetitionCreateDialog extends ConsumerStatefulWidget {
  const CompetitionCreateDialog({
    super.key,
    required this.onCreated,
  });

  final ValueChanged<CompetitionModel> onCreated;

  @override
  ConsumerState<CompetitionCreateDialog> createState() =>
      _CompetitionCreateDialogState();
}

class _CompetitionCreateDialogState
    extends ConsumerState<CompetitionCreateDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _maxMembersController = TextEditingController(text: '50');
  final _entryFeeController = TextEditingController(text: '0.00');

  DateTime? _startDate;
  DateTime? _endDate;
  DateTime? _registrationCloseDate;
  String _scoringMethod = 'net_profit';
  bool _isPrivate = false;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _maxMembersController.dispose();
    _entryFeeController.dispose();
    super.dispose();
  }

  Future<void> _pickDateTime({
    required BuildContext context,
    required ValueChanged<DateTime> onSelected,
    DateTime? initial,
  }) async {
    final now = DateTime.now();
    final initialDate = initial ?? now;
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: DateTime(now.year - 1),
      lastDate: DateTime(now.year + 5),
    );

    if (pickedDate == null || !mounted) return;

    final pickedTime = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initialDate),
    );

    if (pickedTime == null) return;

    onSelected(
      DateTime(
        pickedDate.year,
        pickedDate.month,
        pickedDate.day,
        pickedTime.hour,
        pickedTime.minute,
      ),
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    if (_startDate == null || _endDate == null) {
      context.showError('Please choose start and end date/time.');
      return;
    }

    setState(() {
      _isSubmitting = true;
    });

    final payload = CompetitionCreateInput(
      name: _nameController.text.trim(),
      description: _descriptionController.text.trim(),
      maxMembers: int.tryParse(_maxMembersController.text.trim()) ?? 50,
      startDate: _startDate!,
      endDate: _endDate!,
      registrationCloseDate: _registrationCloseDate,
      entryFee: _entryFeeController.text.trim(),
      scoringMethod: _scoringMethod,
      isPrivate: _isPrivate,
    );

    final result = await ref
        .read(competitionRepositoryProvider)
        .createCompetition(payload);

    if (!mounted) return;

    setState(() {
      _isSubmitting = false;
    });

    if (result.isError) {
      context.showError(result.errorMessage);
      return;
    }

    final created = result.data;
    widget.onCreated(created);
    Navigator.of(context).pop();
    context.showSuccess('Competition created successfully');
  }

  String _dateText(DateTime? value) {
    if (value == null) return 'Pick date & time';
    final date =
        '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
    final time =
        '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';
    return '$date $time';
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;

    return Dialog(
      backgroundColor: colors.always161B22,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
      ),
      child: Container(
        width: 620,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: colors.always30363D),
        ),
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Create Competition',
                  style: TextStyle(
                    color: colors.alwaysWhite,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 16),
                _input(
                  controller: _nameController,
                  label: 'Competition Name',
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Name is required';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                _input(
                  controller: _descriptionController,
                  label: 'Description',
                  maxLines: 3,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Description is required';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _input(
                        controller: _maxMembersController,
                        label: 'Max Members',
                        keyboardType: TextInputType.number,
                        validator: (value) {
                          final parsed = int.tryParse((value ?? '').trim());
                          if (parsed == null || parsed <= 1) {
                            return 'Use at least 2 members';
                          }
                          return null;
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _input(
                        controller: _entryFeeController,
                        label: 'Entry Fee',
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        validator: (value) {
                          final parsed = num.tryParse((value ?? '').trim());
                          if (parsed == null || parsed < 0) {
                            return 'Use 0 or greater';
                          }
                          return null;
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: colors.always0D1117,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: colors.always30363D),
                  ),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<String>(
                      value: _scoringMethod,
                      dropdownColor: colors.always1F242C,
                      style: TextStyle(color: colors.alwaysWhite),
                      isExpanded: true,
                      items: const [
                        DropdownMenuItem(
                          value: 'net_profit',
                          child: Text('Scoring: Net Profit'),
                        ),
                        DropdownMenuItem(
                          value: 'roi',
                          child: Text('Scoring: ROI'),
                        ),
                        DropdownMenuItem(
                          value: 'win_rate',
                          child: Text('Scoring: Win Rate'),
                        ),
                        DropdownMenuItem(
                          value: 'total_payout',
                          child: Text('Scoring: Total Payout'),
                        ),
                      ],
                      onChanged: (value) {
                        if (value == null) return;
                        setState(() {
                          _scoringMethod = value;
                        });
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                _dateTile(
                  label: 'Start Date/Time',
                  value: _dateText(_startDate),
                  onTap: () => _pickDateTime(
                    context: context,
                    initial: _startDate,
                    onSelected: (date) {
                      setState(() {
                        _startDate = date;
                      });
                    },
                  ),
                ),
                const SizedBox(height: 10),
                _dateTile(
                  label: 'End Date/Time',
                  value: _dateText(_endDate),
                  onTap: () => _pickDateTime(
                    context: context,
                    initial: _endDate,
                    onSelected: (date) {
                      setState(() {
                        _endDate = date;
                      });
                    },
                  ),
                ),
                const SizedBox(height: 10),
                _dateTile(
                  label: 'Registration Close Date/Time (optional)',
                  value: _dateText(_registrationCloseDate),
                  onTap: () => _pickDateTime(
                    context: context,
                    initial: _registrationCloseDate,
                    onSelected: (date) {
                      setState(() {
                        _registrationCloseDate = date;
                      });
                    },
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Switch(
                      value: _isPrivate,
                      onChanged: (value) {
                        setState(() {
                          _isPrivate = value;
                        });
                      },
                    ),
                    Text(
                      'Private Competition',
                      style: TextStyle(color: colors.alwaysE6EDF3),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: CustomOutlinedButton.big(
                        text: 'Cancel',
                        textColor: colors.alwaysWhite,
                        onTap: () => Navigator.of(context).pop(),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: CustomButton(
                        text: _isSubmitting ? 'Creating...' : 'Create',
                        onPressed: _isSubmitting ? null : _submit,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _input({
    required TextEditingController controller,
    required String label,
    String? Function(String?)? validator,
    TextInputType? keyboardType,
    int maxLines = 1,
  }) {
    final colors = ref.watch(appThemeProvider).colors;

    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      maxLines: maxLines,
      validator: validator,
      style: TextStyle(color: colors.alwaysWhite),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: TextStyle(color: colors.always8B949E),
        filled: true,
        fillColor: colors.always0D1117,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: colors.always30363D),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: colors.always30363D),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: colors.always52AAFF),
        ),
      ),
    );
  }

  Widget _dateTile({
    required String label,
    required String value,
    required VoidCallback onTap,
  }) {
    final colors = ref.watch(appThemeProvider).colors;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
        decoration: BoxDecoration(
          color: colors.always0D1117,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: colors.always30363D),
        ),
        child: Row(
          children: [
            Icon(Icons.schedule, color: colors.always8B949E, size: 16),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '$label: $value',
                style: TextStyle(color: colors.alwaysE6EDF3),
              ),
            ),
            Icon(Icons.edit_calendar, color: colors.always52AAFF, size: 18),
          ],
        ),
      ),
    );
  }
}
