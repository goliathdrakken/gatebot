# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'KegbotSite'
        db.create_table('core_kegbotsite', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('background_image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal('core', ['KegbotSite'])

        # Adding model 'UserPicture'
        db.create_table('core_userpicture', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('core', ['UserPicture'])

        # Adding model 'UserProfile'
        db.create_table('core_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('gender', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('weight', self.gf('django.db.models.fields.FloatField')()),
            ('mugshot', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.UserPicture'], null=True, blank=True)),
        ))
        db.send_create_signal('core', ['UserProfile'])

        # Adding model 'AuthenticationToken'
        db.create_table('core_authenticationtoken', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='tokens', to=orm['core.KegbotSite'])),
            ('seqn', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('auth_device', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('token_value', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('nice_name', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('pin', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('expires', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['AuthenticationToken'])

        # Adding unique constraint on 'AuthenticationToken', fields ['site', 'seqn', 'auth_device', 'token_value']
        db.create_unique('core_authenticationtoken', ['site_id', 'seqn', 'auth_device', 'token_value'])

        # Adding model 'RelayLog'
        db.create_table('core_relaylog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='relaylogs', to=orm['core.KegbotSite'])),
            ('seqn', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('time', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('core', ['RelayLog'])

        # Adding unique constraint on 'RelayLog', fields ['site', 'seqn']
        db.create_unique('core_relaylog', ['site_id', 'seqn'])

        # Adding model 'Config'
        db.create_table('core_config', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='configs', to=orm['core.KegbotSite'])),
            ('key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('core', ['Config'])

        # Adding model 'SystemStats'
        db.create_table('core_systemstats', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.KegbotSite'])),
            ('date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('stats', self.gf('django.db.models.fields.TextField')(default='{}')),
        ))
        db.send_create_signal('core', ['SystemStats'])

        # Adding model 'UserStats'
        db.create_table('core_userstats', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.KegbotSite'])),
            ('date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('stats', self.gf('django.db.models.fields.TextField')(default='{}')),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='stats', unique=True, to=orm['auth.User'])),
        ))
        db.send_create_signal('core', ['UserStats'])

        # Adding model 'SystemEvent'
        db.create_table('core_systemevent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(related_name='events', to=orm['core.KegbotSite'])),
            ('seqn', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('when', self.gf('django.db.models.fields.DateTimeField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='events', null=True, to=orm['auth.User'])),
            ('drink', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='events', null=True, to=orm['core.Drink'])),
            ('keg', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='events', null=True, to=orm['core.Keg'])),
            ('session', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='events', null=True, to=orm['core.DrinkingSession'])),
        ))
        db.send_create_signal('core', ['SystemEvent'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'RelayLog', fields ['site', 'seqn']
        db.delete_unique('core_relaylog', ['site_id', 'seqn'])

        # Removing unique constraint on 'AuthenticationToken', fields ['site', 'seqn', 'auth_device', 'token_value']
        db.delete_unique('core_authenticationtoken', ['site_id', 'seqn', 'auth_device', 'token_value'])

        # Deleting model 'KegbotSite'
        db.delete_table('core_kegbotsite')

        # Deleting model 'UserPicture'
        db.delete_table('core_userpicture')

        # Deleting model 'UserProfile'
        db.delete_table('core_userprofile')

        # Deleting model 'AuthenticationToken'
        db.delete_table('core_authenticationtoken')

        # Deleting model 'RelayLog'
        db.delete_table('core_relaylog')

        # Deleting model 'Config'
        db.delete_table('core_config')

        # Deleting model 'SystemStats'
        db.delete_table('core_systemstats')

        # Deleting model 'UserStats'
        db.delete_table('core_userstats')

        # Deleting model 'SystemEvent'
        db.delete_table('core_systemevent')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'core.authenticationtoken': {
            'Meta': {'unique_together': "(('site', 'seqn', 'auth_device', 'token_value'),)", 'object_name': 'AuthenticationToken'},
            'auth_device': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nice_name': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'pin': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'seqn': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tokens'", 'to': "orm['core.KegbotSite']"}),
            'token_value': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'core.config': {
            'Meta': {'object_name': 'Config'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'configs'", 'to': "orm['core.KegbotSite']"}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'core.kegbotsite': {
            'Meta': {'object_name': 'KegbotSite'},
            'background_image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'core.relaylog': {
            'Meta': {'unique_together': "(('site', 'seqn'),)", 'object_name': 'RelayLog'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'seqn': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relaylogs'", 'to': "orm['core.KegbotSite']"}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'time': ('django.db.models.fields.DateTimeField', [], {})
        },
        'core.systemevent': {
            'Meta': {'ordering': "('-when', '-id')", 'object_name': 'SystemEvent'},
            'drink': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['core.Drink']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keg': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['core.Keg']"}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'seqn': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'session': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['core.DrinkingSession']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['core.KegbotSite']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['auth.User']"}),
            'when': ('django.db.models.fields.DateTimeField', [], {})
        },
        'core.systemstats': {
            'Meta': {'object_name': 'SystemStats'},
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.KegbotSite']"}),
            'stats': ('django.db.models.fields.TextField', [], {'default': "'{}'"})
        },
        'core.userpicture': {
            'Meta': {'object_name': 'UserPicture'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'core.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mugshot': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.UserPicture']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'weight': ('django.db.models.fields.FloatField', [], {})
        },
        'core.userstats': {
            'Meta': {'object_name': 'UserStats'},
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.KegbotSite']"}),
            'stats': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stats'", 'unique': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['core']
