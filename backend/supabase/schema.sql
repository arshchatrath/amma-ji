-- Amma ji recipe sheet in Supabase. Run this once in the SQL editor, then load the rows with
-- scripts/push_supabase.py. Anyone can read; only the service key (kept on the backend) can write.

create table if not exists dishes (
  id text primary key,
  name_en text not null,
  name_hinglish text,
  name_hi text,
  name_pa text,
  kind text,
  diet text,
  allergens text[] default '{}',
  servings jsonb,
  prep_min int,
  cook_min int,
  total_min int,
  course text,
  cuisine text,
  nutrition_per_serving jsonb,
  has_steps boolean default false,
  source_link text,
  source_note text
);

create table if not exists dish_ingredients (
  dish_id text references dishes(id) on delete cascade,
  n int,
  ingredient_id text not null,
  as_written text,
  qty numeric,
  unit text,
  essential boolean default false,
  substitutes text[] default '{}',
  primary key (dish_id, n)
);

create table if not exists steps (
  dish_id text references dishes(id) on delete cascade,
  n int,
  text_en text,
  text_hinglish text,
  text_hi text,
  text_pa text,
  uses text[] default '{}',
  timer_min int,
  safety_en text,
  safety_hinglish text,
  safety_hi text,
  safety_pa text,
  primary key (dish_id, n)
);

create table if not exists mistakes (
  dish_id text references dishes(id) on delete cascade,
  n int,
  mistake text,
  fix_en text,
  fix_hi text,
  primary key (dish_id, n)
);

create index if not exists dish_ingredients_by_ingredient on dish_ingredients (ingredient_id);

alter table dishes enable row level security;
alter table dish_ingredients enable row level security;
alter table steps enable row level security;
alter table mistakes enable row level security;

drop policy if exists "anyone can read" on dishes;
drop policy if exists "anyone can read" on dish_ingredients;
drop policy if exists "anyone can read" on steps;
drop policy if exists "anyone can read" on mistakes;
create policy "anyone can read" on dishes for select using (true);
create policy "anyone can read" on dish_ingredients for select using (true);
create policy "anyone can read" on steps for select using (true);
create policy "anyone can read" on mistakes for select using (true);
