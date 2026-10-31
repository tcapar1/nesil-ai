begin;
select plan(15);

insert into auth.users(id,instance_id,aud,role,email,encrypted_password,email_confirmed_at,raw_app_meta_data,raw_user_meta_data,created_at,updated_at)
values
 ('00000000-0000-4000-8000-000000000001','00000000-0000-0000-0000-000000000000','authenticated','authenticated','rls-a@example.test','',now(),'{}','{"display_name":"A"}',now(),now()),
 ('00000000-0000-4000-8000-000000000002','00000000-0000-0000-0000-000000000000','authenticated','authenticated','rls-b@example.test','',now(),'{}','{"display_name":"B"}',now(),now());
insert into public.nesil_conversations(id,user_id,title) values
 ('10000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001','A sohbeti'),
 ('10000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000002','B sohbeti');
insert into public.nesil_messages(conversation_id,role,content) values
 ('10000000-0000-4000-8000-000000000001','user','A mesajı'),
 ('10000000-0000-4000-8000-000000000002','user','B mesajı');
insert into public.nesil_memory_items(id,user_id,memory_text) values
 ('20000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001','A hafızası'),
 ('20000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000002','B hafızası');
insert into public.nesil_documents(id,user_id,object_path,file_name,file_size,content_type) values
 ('30000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001/a.pdf','a.pdf',3,'application/pdf'),
 ('30000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000002/b.pdf','b.pdf',3,'application/pdf');
insert into storage.objects(bucket_id,name) values
 ('nesil-user-files','00000000-0000-4000-8000-000000000001/a.pdf'),
 ('nesil-user-files','00000000-0000-4000-8000-000000000002/b.pdf');

select is((select count(*)::int from public.nesil_profiles),2,'Auth trigger creates profiles for both isolated users');
set local role authenticated;
select set_config('request.jwt.claim.sub','00000000-0000-4000-8000-000000000001',true);
select is((select count(*)::int from public.nesil_profiles),1,'user A sees only own profile');
select is((select count(*)::int from public.nesil_conversations),1,'user A sees only own conversations');
select is((select count(*)::int from public.nesil_messages),1,'user A sees messages only through owned conversation');
select is((select count(*)::int from public.nesil_memory_items),1,'user A sees only own memory');
select is((select count(*)::int from public.nesil_documents),1,'user A sees only own document metadata');
select is((select count(*)::int from storage.objects where bucket_id='nesil-user-files'),1,'user A sees only own Storage object row');
select is((select count(*)::int from public.nesil_conversations where id='10000000-0000-4000-8000-000000000002'),0,'user A cannot read user B conversation by id');
select is((select count(*)::int from public.nesil_messages where content='B mesajı'),0,'user A cannot read user B messages');
select is((select count(*)::int from public.nesil_memory_items where id='20000000-0000-4000-8000-000000000002'),0,'user A cannot read user B memory');
select is((select count(*)::int from public.nesil_documents where id='30000000-0000-4000-8000-000000000002'),0,'user A cannot read user B document metadata');
select is((with changed as (update public.nesil_conversations set title='hijack' where id='10000000-0000-4000-8000-000000000002' returning 1) select count(*)::int from changed),0,'user A cannot update user B conversation');
select is((with changed as (delete from public.nesil_memory_items where id='20000000-0000-4000-8000-000000000002' returning 1) select count(*)::int from changed),0,'user A cannot delete user B memory');
select throws_ok($$insert into public.nesil_conversations(user_id,title) values ('00000000-0000-4000-8000-000000000002','hijack')$$,'42501',null,'user A cannot insert a conversation for user B');
select throws_ok($$insert into storage.objects(bucket_id,name) values ('nesil-user-files','00000000-0000-4000-8000-000000000002/attack.pdf')$$,'42501',null,'user A cannot create a Storage object in user B folder');
select is((with changed as (delete from storage.objects where bucket_id='nesil-user-files' and name='00000000-0000-4000-8000-000000000002/b.pdf' returning 1) select count(*)::int from changed),0,'user A cannot delete user B Storage object');
select * from finish();
rollback;
