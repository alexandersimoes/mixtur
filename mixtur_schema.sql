CREATE TABLE "user" (name text,email text, password text);
CREATE TABLE "vote" (
  id integer primary key autoincrement,
  user string not null,
  song integer not null,
  FOREIGN KEY(user) REFERENCES user(name),
  FOREIGN KEY(song) REFERENCES song(id)
);
CREATE TABLE mixanthology(
    mix_id INTEGER,
    anthology_id INTEGER,
    FOREIGN KEY(mix_id) REFERENCES mix(id) ON DELETE CASCADE,
    FOREIGN KEY(anthology_id) REFERENCES anthology(id) ON DELETE CASCADE,
    PRIMARY KEY (mix_id, anthology_id)
);
CREATE INDEX mixindex ON mixanthology(mix_id);
CREATE INDEX anthologyindex ON mixanthology(anthology_id);
CREATE TABLE "song" (
	`id`	integer PRIMARY KEY AUTOINCREMENT,
	`title`	string NOT NULL,
	`artist`	string NOT NULL,
	`position`	integer NOT NULL,
	`runtime`	TEXT,
	`disc`	INTEGER,
	`slug`	string,
	`mix`	integer NOT NULL
);
CREATE TABLE "anthology" (
	`id`	integer PRIMARY KEY AUTOINCREMENT,
	`name`	string,
	`slug`	string
);
CREATE TABLE "mix" (
	`id`	integer PRIMARY KEY AUTOINCREMENT,
	`name`	string,
	`date`	string NOT NULL,
	`desc`	string,
	`cover`	string,
	`user`	string NOT NULL,
	`slug`	string,
	`palette`	string
);
CREATE TABLE listen (
	`user`	string,
	`mix`	integer NOT NULL,
	`song`	integer NOT NULL,
	`time`	TIMESTAMP
  DEFAULT CURRENT_TIMESTAMP
);

