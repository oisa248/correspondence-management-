create table if not exists users (
  id serial primary key, name text not null, email text unique not null,
  role text not null, password_hash text not null);
create sequence if not exists ref_seq;
create table if not exists correspondence (
  id serial primary key, type text not null, subject text not null, body text default '',
  sender text default '', status text not null, ref_no text, category text, cc text,
  created_by int references users(id), approver_id int references users(id),
  assignee_id int references users(id), stamped boolean default false, signed_by text,
  registered_at timestamptz, created_at timestamptz default now(), updated_at timestamptz default now());
create table if not exists attachments (
  id serial primary key, corr_id int references correspondence(id) on delete cascade,
  filename text, mime text, data bytea);
create table if not exists events (
  id serial primary key, corr_id int references correspondence(id) on delete cascade,
  actor text, action text, from_status text, to_status text, note text, at timestamptz default now());
