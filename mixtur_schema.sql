drop table if exists user;
create table user (
  id integer primary key autoincrement,
  name string not null,
  email string not null,
  password string not null
);

drop table if exists mix;
create table mix (
  id integer primary key autoincrement,
  name string not null,
  date string not null,
  description string null,
  cover string null,
  user integer not null,
  FOREIGN KEY(user) REFERENCES user(id)
);

drop table if exists song;
create table song (
  id integer primary key autoincrement,
  title string not null,
  artist string not null,
  position integer not null,
  runtime string,
  disc integer,
  mix integer not null,
  FOREIGN KEY(mix) REFERENCES mix(id)
);

drop table if exists vote;
create table vote (
  id integer primary key autoincrement,
  user integer not null,
  song integer not null,
  FOREIGN KEY(user) REFERENCES user(id),
  FOREIGN KEY(song) REFERENCES song(id)
);

drop table if exists anthology;
create table anthology (
    id integer primary key autoincrement,
    name string
);

drop table if exists mixanthology;
CREATE TABLE mixanthology(
    mix_id INTEGER,
    anthology_id INTEGER,
    FOREIGN KEY(mix_id) REFERENCES mix(id) ON DELETE CASCADE,
    FOREIGN KEY(anthology_id) REFERENCES anthology(id) ON DELETE CASCADE,
    PRIMARY KEY (mix_id, anthology_id)
);
CREATE INDEX mixindex ON mixanthology(mix_id);
CREATE INDEX anthologyindex ON mixanthology(anthology_id);