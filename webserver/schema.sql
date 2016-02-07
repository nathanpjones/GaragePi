--drop table if exists entries;
create table if not exists entries (
  ID integer primary key autoincrement,
  Timestamp datetime default current_timestamp,
  UserAgent text,
  Login text,
  Event text,
  Description text
);