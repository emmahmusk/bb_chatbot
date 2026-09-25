class SportsbookProvider {
  final String id;
  final String name;

  const SportsbookProvider({required this.id, required this.name});

  factory SportsbookProvider.fromJson(dynamic json) {
    if (json is String) return SportsbookProvider(id: json, name: _title(json));
    final map = Map<String, dynamic>.from(json as Map);
    final id = (map['id'] ?? map['key'] ?? map['name'] ?? '').toString();
    return SportsbookProvider(id: id, name: (map['name'] ?? _title(id)).toString());
  }
}

class SportsbookSport {
  final String id;
  final String name;

  const SportsbookSport({required this.id, required this.name});

  factory SportsbookSport.fromJson(Map<String, dynamic> json) {
    final id = (json['id'] ?? json['key'] ?? json['sport'] ?? '').toString();
    return SportsbookSport(id: id, name: (json['name'] ?? _title(id)).toString());
  }
}

class SportsbookLeague {
  final String id;
  final String name;

  const SportsbookLeague({required this.id, required this.name});

  factory SportsbookLeague.fromJson(Map<String, dynamic> json) {
    final id = (json['id'] ?? json['key'] ?? json['league'] ?? '').toString();
    return SportsbookLeague(id: id, name: (json['name'] ?? _title(id)).toString());
  }
}

class SportsbookFixture {
  final String id;
  final String event;
  final String homeTeam;
  final String awayTeam;
  final String sport;
  final String league;
  final DateTime? startDate;
  final bool isLive;

  const SportsbookFixture({required this.id, required this.event, required this.homeTeam, required this.awayTeam, required this.sport, required this.league, required this.startDate, required this.isLive});

  factory SportsbookFixture.fromJson(Map<String, dynamic> json) {
    return SportsbookFixture(
      id: (json['fixture_id'] ?? json['id'] ?? '').toString(),
      event: (json['event'] ?? json['name'] ?? '').toString(),
      homeTeam: (json['home_team'] ?? json['home_team_display'] ?? '').toString(),
      awayTeam: (json['away_team'] ?? json['away_team_display'] ?? '').toString(),
      sport: (json['sport'] ?? '').toString(),
      league: (json['league'] ?? '').toString(),
      startDate: DateTime.tryParse((json['start_date'] ?? '').toString()),
      isLive: json['is_live'] == true || ['live', 'in_play', 'in-play'].contains(json['status'].toString().toLowerCase()),
    );
  }
}

class SportsbookOdd {
  final String fixtureId;
  final String event;
  final String sport;
  final String league;
  final String sportsbook;
  final String market;
  final String selection;
  final String price;
  final double decimal;
  final String? deepLink;

  const SportsbookOdd({required this.fixtureId, required this.event, required this.sport, required this.league, required this.sportsbook, required this.market, required this.selection, required this.price, required this.decimal, this.deepLink});

  factory SportsbookOdd.fromJson(Map<String, dynamic> json) {
    return SportsbookOdd(
      fixtureId: (json['fixture_id'] ?? '').toString(),
      event: (json['event'] ?? '').toString(),
      sport: (json['sport'] ?? '').toString(),
      league: (json['league'] ?? '').toString(),
      sportsbook: (json['sportsbook'] ?? '').toString().toLowerCase(),
      market: (json['market'] ?? 'moneyline').toString(),
      selection: (json['selection'] ?? '').toString(),
      price: (json['price'] ?? '').toString(),
      decimal: double.tryParse((json['decimal'] ?? 0).toString()) ?? 0,
      deepLink: json['deep_link']?.toString(),
    );
  }
}

class SportsbookSelection {
  final SportsbookOdd hardRock;
  final List<SportsbookOdd> snapshot;

  const SportsbookSelection({required this.hardRock, required this.snapshot});

  Map<String, dynamic> toJson() => {
        'fixture_id': hardRock.fixtureId,
        'event': hardRock.event,
        'sport': hardRock.sport,
        'league': hardRock.league,
        'market': hardRock.market,
        'selection': hardRock.selection,
        'odds_snapshot': snapshot.map((odd) => {
              'fixture_id': odd.fixtureId,
              'event': odd.event,
              'sport': odd.sport,
              'league': odd.league,
              'sportsbook': odd.sportsbook,
              'market': odd.market,
              'selection': odd.selection,
              'price': odd.price,
              'decimal': odd.decimal,
              'deep_link': odd.deepLink,
            }).toList(),
      };
}

String _title(String value) => value.replaceAll('_', ' ').split(' ').map((word) => word.isEmpty ? word : '${word[0].toUpperCase()}${word.substring(1)}').join(' ');
