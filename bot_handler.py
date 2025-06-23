"""
Telegram Bot Handler for Video Downloader
"""

import os
import time
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from downloader import VideoDownloader
from config import Config

logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram Bot class for handling messages and downloads"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api_url = config.telegram_api_url
        self.last_update_id = 0
        self.known_users = set()
        self.download_stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_users': 0
        }
        self.downloader = VideoDownloader(config)
        
        # Load known users from file if exists
        self._load_user_data()
    
    def _load_user_data(self):
        """Load user data from file"""
        try:
            if os.path.exists('users.json'):
                with open('users.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.known_users = set(data.get('known_users', []))
                    self.download_stats = data.get('stats', self.download_stats)
                    # Ensure total_users matches actual known_users count
                    self.download_stats['total_users'] = len(self.known_users)
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
    
    def _save_user_data(self):
        """Save user data to file"""
        try:
            data = {
                'known_users': list(self.known_users),
                'stats': self.download_stats,
                'last_updated': datetime.now().isoformat()
            }
            with open('users.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
    
    def get_updates(self) -> List[Dict[str, Any]]:
        """Get updates from Telegram API"""
        try:
            response = requests.get(
                self.api_url + 'getUpdates',
                params={'offset': self.last_update_id + 1, 'timeout': 30},
                timeout=35
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['ok'] and data['result']:
                    self.last_update_id = data['result'][-1]['update_id']
                    return data['result']
            else:
                logger.error(f"Error getting updates: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error getting updates: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting updates: {e}")
        
        return []
    
    def send_message(self, chat_id: int, text: str, parse_mode: str = None) -> bool:
        """Send a message to a chat"""
        try:
            data = {
                'chat_id': chat_id,
                'text': text[:4096]  # Telegram message limit
            }
            if parse_mode:
                data['parse_mode'] = parse_mode
            
            response = requests.post(
                self.api_url + 'sendMessage',
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('ok', False)
            else:
                logger.error(f"Error sending message: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_file(self, chat_id: int, file_path: str, caption: str = None) -> bool:
        """Send a file to a chat - automatically detects if it's a video, image, or document"""
        try:
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.config.MAX_FILE_SIZE:
                self.send_message(
                    chat_id,
                    f"❌ الملف كبير جداً ({file_size / 1024 / 1024:.1f} MB)\n"
                    f"الحد الأقصى: {self.config.MAX_FILE_SIZE / 1024 / 1024:.1f} MB"
                )
                return False
            
            # Determine file type
            file_ext = os.path.splitext(file_path)[1].lower()
            is_video = file_ext in ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv']
            is_image = file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            
            with open(file_path, 'rb') as f:
                data = {'chat_id': chat_id}
                if caption:
                    data['caption'] = caption[:1024]  # Telegram caption limit
                
                # Choose appropriate Telegram API endpoint based on file type
                if is_video:
                    files = {'video': f}
                    endpoint = 'sendVideo'
                    # Add video-specific parameters
                    data['supports_streaming'] = True
                elif is_image:
                    files = {'photo': f}
                    endpoint = 'sendPhoto'
                else:
                    files = {'document': f}
                    endpoint = 'sendDocument'
                
                response = requests.post(
                    self.api_url + endpoint,
                    data=data,
                    files=files,
                    timeout=300  # 5 minutes for file upload
                )
                
                if response.status_code == 200:
                    return response.json().get('ok', False)
                else:
                    logger.error(f"Error sending {endpoint}: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            return False
    
    def get_bot_info(self) -> Dict[str, Any]:
        """Get bot information"""
        try:
            response = requests.get(self.api_url + 'getMe', timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['ok']:
                    return data['result']
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
        return {}
    
    def handle_start_command(self, chat_id: int, user_info: Dict[str, Any]):
        """Handle /start command"""
        user_id = chat_id
        user_name = user_info.get('first_name', 'بدون اسم')
        username = user_info.get('username', 'بدون اسم مستخدم')
        
        # Add user to known users
        if user_id not in self.known_users:
            self.known_users.add(user_id)
            self.download_stats['total_users'] = len(self.known_users)
            self._save_user_data()
            
            # Notify admin
            if self.config.ADMIN_ID:
                admin_message = (
                    f"🆕 مستخدم جديد دخل البوت:\n"
                    f"👤 الاسم: {user_name}\n"
                    f"🔗 المعرف: @{username}\n"
                    f"🆔 ID: {user_id}\n"
                    f"📈 العدد الكلي: {len(self.known_users)}"
                )
                self.send_message(self.config.ADMIN_ID, admin_message)
        
        # Welcome message
        welcome_message = (
            f"مرحباً {user_name}! 👋\n\n"
            "🎥 أرسل رابط الفيديو وسأقوم بتحميله لك\n"
            "ℹ️ أو استخدم /info [الرابط] لمعرفة تفاصيل الفيديو\n"
            "👤 أو استخدم /account [الرابط] لمعرفة معلومات الحساب والموقع\n\n"
            "📱 المنصات المدعومة:\n"
            "• YouTube\n"
            "• Instagram\n"
            "• TikTok\n"
            "• Twitter\n"
            "• Facebook\n"
            "• وغيرها الكثير...\n\n"
            "📋 الأوامر المتاحة:\n"
            "• /help - تعليمات الاستخدام\n"
            "• /info [رابط] - معلومات الفيديو والمالك\n\n"
            "⚡ فقط أرسل الرابط وانتظر!"
        )
        self.send_message(chat_id, welcome_message)
    
    def handle_info_command(self, chat_id: int, url: str):
        """Handle /info command to show video information without downloading"""
        try:
            self.send_message(chat_id, "🔍 جاري استخراج معلومات الفيديو...")
            
            # Get video info without downloading
            result = self.downloader.get_video_info(url)
            
            if result['success']:
                video_info = result['info']
                
                # Build detailed info message
                info_message = f"📹 معلومات الفيديو:\n\n"
                info_message += f"🎥 العنوان: {video_info.get('title', 'غير متاح')}\n"
                
                # Owner/Channel information
                if video_info.get('uploader'):
                    info_message += f"👤 صاحب القناة: {video_info['uploader']}\n"
                if video_info.get('uploader_id'):
                    info_message += f"🆔 معرف المالك: {video_info['uploader_id']}\n"
                if video_info.get('channel'):
                    info_message += f"📺 اسم القناة: {video_info['channel']}\n"
                if video_info.get('channel_id'):
                    info_message += f"🔗 معرف القناة: {video_info['channel_id']}\n"
                if video_info.get('uploader_url'):
                    info_message += f"🌐 رابط القناة: {video_info['uploader_url']}\n"
                
                # Location information
                if video_info.get('location'):
                    info_message += f"📍 الموقع: {video_info['location']}\n"
                if video_info.get('creator'):
                    info_message += f"✍️ المنشئ: {video_info['creator']}\n"
                if video_info.get('artist'):
                    info_message += f"🎨 الفنان: {video_info['artist']}\n"
                
                # Video details
                if video_info.get('description'):
                    desc = video_info['description'][:200] + "..." if len(video_info['description']) > 200 else video_info['description']
                    info_message += f"📝 الوصف: {desc}\n"
                
                if video_info.get('duration'):
                    duration = int(video_info['duration'])
                    info_message += f"⏱️ المدة: {duration // 60}:{duration % 60:02d}\n"
                
                if video_info.get('view_count'):
                    info_message += f"👀 المشاهدات: {video_info['view_count']:,}\n"
                
                if video_info.get('like_count'):
                    info_message += f"👍 الإعجابات: {video_info['like_count']:,}\n"
                
                if video_info.get('upload_date'):
                    upload_date = video_info['upload_date']
                    formatted_date = f"{upload_date[6:8]}/{upload_date[4:6]}/{upload_date[:4]}"
                    info_message += f"📅 تاريخ النشر: {formatted_date}\n"
                
                if video_info.get('webpage_url'):
                    info_message += f"\n🔗 الرابط الأصلي: {video_info['webpage_url']}\n"
                
                # File info
                if video_info.get('filesize'):
                    size_mb = video_info['filesize'] / (1024 * 1024)
                    info_message += f"📦 حجم الملف: {size_mb:.1f} MB\n"
                elif video_info.get('filesize_approx'):
                    size_mb = video_info['filesize_approx'] / (1024 * 1024)
                    info_message += f"📦 حجم الملف (تقريبي): {size_mb:.1f} MB\n"
                
                info_message += f"\n💡 لتحميل الفيديو، أرسل الرابط مباشرة"
                
                self.send_message(chat_id, info_message)
            else:
                error_message = f"❌ فشل في استخراج معلومات الفيديو: {result.get('error', 'خطأ غير معروف')}"
                self.send_message(chat_id, error_message)
                
        except Exception as e:
            logger.error(f"Error handling info command: {e}")
            self.send_message(chat_id, f"❌ خطأ في استخراج المعلومات: {str(e)}")
    
    def handle_account_command(self, chat_id: int, url: str):
        """Handle /account command to show detailed account information including location"""
        try:
            self.send_message(chat_id, "🔍 جاري استخراج معلومات الحساب والموقع...")
            
            # Try to get channel info first (for profile URLs)
            result = self.downloader.get_channel_info(url)
            
            # If that fails, try video info (for video URLs)
            if not result['success']:
                result = self.downloader.get_video_info(url)
            
            if result['success']:
                video_info = result['info']
                info_type = result.get('type', 'video')
                
                # Build detailed account info message
                if info_type == 'channel':
                    info_message = f"📺 معلومات القناة/الحساب:\n\n"
                else:
                    info_message = f"👤 معلومات الحساب:\n\n"
                
                # Basic account info
                if video_info.get('uploader'):
                    info_message += f"📱 اسم الحساب: {video_info['uploader']}\n"
                if video_info.get('uploader_id'):
                    info_message += f"🆔 معرف الحساب: {video_info['uploader_id']}\n"
                if video_info.get('channel'):
                    info_message += f"📺 اسم القناة: {video_info['channel']}\n"
                if video_info.get('channel_id'):
                    info_message += f"🔗 معرف القناة: {video_info['channel_id']}\n"
                if video_info.get('uploader_url'):
                    info_message += f"🌐 رابط الحساب: {video_info['uploader_url']}\n"
                
                # Playlist/Channel specific info
                if video_info.get('playlist_title'):
                    info_message += f"📂 عنوان القناة: {video_info['playlist_title']}\n"
                if video_info.get('playlist_count'):
                    info_message += f"🎥 عدد الفيديوهات: {video_info['playlist_count']:,}\n"
                if video_info.get('playlist_description'):
                    desc = video_info['playlist_description'][:200] + "..." if len(video_info['playlist_description']) > 200 else video_info['playlist_description']
                    info_message += f"📝 وصف القناة: {desc}\n"
                
                # Location and country information
                location_found = False
                if video_info.get('location'):
                    info_message += f"\n📍 الموقع: {video_info['location']}\n"
                    location_found = True
                
                # Try to extract country from various fields
                country_info = self._extract_country_info(video_info)
                if country_info:
                    info_message += f"{country_info}\n"
                    location_found = True
                
                # Creator and artist info
                if video_info.get('creator'):
                    info_message += f"✍️ المنشئ: {video_info['creator']}\n"
                if video_info.get('artist'):
                    info_message += f"🎨 الفنان: {video_info['artist']}\n"
                
                # Video count and subscriber info if available
                if video_info.get('channel_follower_count'):
                    info_message += f"👥 المتابعون: {video_info['channel_follower_count']:,}\n"
                if video_info.get('uploader_video_count'):
                    info_message += f"🎥 عدد الفيديوهات: {video_info['uploader_video_count']:,}\n"
                
                if not location_found:
                    info_message += f"\n❌ لم يتم العثور على معلومات الموقع\n"
                    info_message += f"💡 بعض المنصات لا تكشف عن الموقع الجغرافي\n"
                
                info_message += f"\n🔗 رابط الفيديو: {video_info.get('webpage_url', url)}"
                
                self.send_message(chat_id, info_message)
            else:
                error_message = f"❌ فشل في استخراج معلومات الحساب: {result.get('error', 'خطأ غير معروف')}"
                self.send_message(chat_id, error_message)
                
        except Exception as e:
            logger.error(f"Error handling account command: {e}")
            self.send_message(chat_id, f"❌ خطأ في استخراج معلومات الحساب: {str(e)}")
    
    def _extract_country_info(self, video_info: Dict[str, Any]) -> str:
        """Extract country and flag information from video metadata"""
        country_info = ""
        
        # Country mapping with flags
        country_flags = {
            'saudi arabia': '🇸🇦 السعودية',
            'united states': '🇺🇸 الولايات المتحدة',
            'united kingdom': '🇬🇧 المملكة المتحدة',
            'france': '🇫🇷 فرنسا',
            'germany': '🇩🇪 ألمانيا',
            'egypt': '🇪🇬 مصر',
            'uae': '🇦🇪 الإمارات',
            'emirates': '🇦🇪 الإمارات',
            'kuwait': '🇰🇼 الكويت',
            'qatar': '🇶🇦 قطر',
            'bahrain': '🇧🇭 البحرين',
            'oman': '🇴🇲 عمان',
            'jordan': '🇯🇴 الأردن',
            'lebanon': '🇱🇧 لبنان',
            'syria': '🇸🇾 سوريا',
            'iraq': '🇮🇶 العراق',
            'turkey': '🇹🇷 تركيا',
            'iran': '🇮🇷 إيران',
            'pakistan': '🇵🇰 باكستان',
            'india': '🇮🇳 الهند',
            'morocco': '🇲🇦 المغرب',
            'algeria': '🇩🇿 الجزائر',
            'tunisia': '🇹🇳 تونس',
            'libya': '🇱🇾 ليبيا',
            'sudan': '🇸🇩 السودان'
        }
        
        # Check various fields for country information
        location_fields = [
            video_info.get('location', ''),
            video_info.get('uploader', ''),
            video_info.get('description', ''),
            video_info.get('channel', ''),
            video_info.get('creator', '')
        ]
        
        location_text = ' '.join(str(field).lower() for field in location_fields if field)
        
        # Search for country matches
        for country, flag_text in country_flags.items():
            if country in location_text:
                country_info += f"🏳️ الدولة: {flag_text}\n"
                break
        
        # Check for direct country code or geo info
        if video_info.get('country_code'):
            country_code = video_info['country_code'].upper()
            country_info += f"🌍 رمز الدولة: {country_code}\n"
        
        return country_info
    
    def handle_url_message(self, chat_id: int, url: str):
        """Handle URL message for video download"""
        try:
            # Check for TikTok photos first and handle specially
            if 'tiktok.com' in url.lower() and '/photo/' in url.lower():
                self.send_message(chat_id, "❌ صور TikTok غير مدعومة حالياً. جرب إرسال رابط فيديو TikTok بدلاً من ذلك.")
                return
            
            # Send processing message with platform-specific notes
            processing_msg = "⏳ جاري التحميل... يرجى الانتظار"
            if 'snapchat.com' in url.lower():
                processing_msg = "⏳ جاري تحميل السناب شات... محاولة الحصول على جودة أصلية بدون علامات مائية..."
            
            self.send_message(chat_id, processing_msg)
            
            # Update stats
            self.download_stats['total_downloads'] += 1
            
            # Download video
            result = self.downloader.download_video(url)
            
            if result['success']:
                file_path = result['file_path']
                video_info = result.get('info', {})
                
                # Determine content type and prepare caption
                file_ext = os.path.splitext(file_path)[1].lower()
                is_image = file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']
                content_type = "صورة" if is_image else "فيديو"
                emoji = "🖼️" if is_image else "🎥"
                
                # Send file without any caption - completely clean
                if self.send_file(chat_id, file_path, None):
                    self.download_stats['successful_downloads'] += 1
                    self.send_message(chat_id, "✅ تم التحميل بنجاح!")
                else:
                    self.download_stats['failed_downloads'] += 1
                    self.send_message(chat_id, "❌ فشل في إرسال الملف")
                
                # Clean up
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"Error removing file {file_path}: {e}")
            else:
                self.download_stats['failed_downloads'] += 1
                error_msg = result.get('error', 'خطأ غير معروف')
                error_message = f"❌ فشل التحميل: {error_msg}"
                
                # Add helpful suggestions for platform-specific errors
                if 'انستقرام' in error_msg or 'Instagram' in error_msg:
                    error_message += (
                        "\n\n💡 بدائل للانستقرام:\n"
                        "• جرب TikTok أو YouTube للحصول على نتائج أفضل\n"
                        "• استخدم /platforms لمعرفة المنصات الأكثر نجاحاً\n"
                        "• حاول مع رابط انستقرام آخر لاحقاً"
                    )
                elif 'سناب شات' in error_msg or 'snapchat' in error_msg.lower():
                    error_message += (
                        "\n\n💡 معلومات حول السناب شات:\n"
                        "• قصص السناب شات قد تتطلب وقتاً أطول للمعالجة\n"
                        "• تأكد من أن الرابط يحتوي على فيديو وليس صورة\n"
                        "• جرب مع قصة سناب شات أخرى\n"
                        "• الروابط المنتهية الصلاحية لن تعمل"
                    )
                
                self.send_message(chat_id, error_message)
            
            # Save stats
            self._save_user_data()
            
        except Exception as e:
            logger.error(f"Error handling URL message: {e}")
            self.download_stats['failed_downloads'] += 1
            self.send_message(chat_id, f"❌ خطأ في التحميل: {str(e)}")
            self._save_user_data()
    
    def handle_message(self, message: Dict[str, Any]):
        """Handle incoming message"""
        try:
            chat_id = message['chat']['id']
            user_info = message.get('from', {})
            
            # Track user even for non-start commands
            user_id = chat_id
            if user_id not in self.known_users:
                self.known_users.add(user_id)
                self.download_stats['total_users'] = len(self.known_users)
                self._save_user_data()
                
                # Notify admin for new user
                user_name = user_info.get('first_name', 'بدون اسم')
                username = user_info.get('username', 'بدون اسم مستخدم')
                if self.config.ADMIN_ID:
                    admin_message = (
                        f"🆕 مستخدم جديد:\n"
                        f"👤 الاسم: {user_name}\n"
                        f"🔗 المعرف: @{username}\n"
                        f"🆔 ID: {user_id}\n"
                        f"📈 العدد الكلي: {len(self.known_users)}"
                    )
                    self.send_message(self.config.ADMIN_ID, admin_message)
            
            # Handle commands
            if message.get('text', '').startswith('/'):
                if message['text'] == '/start':
                    self.handle_start_command(chat_id, user_info)
                elif message['text'] == '/help':
                    help_message = (
                        "📖 تعليمات استخدام البوت:\n\n"
                        "🎥 لتحميل فيديو: أرسل الرابط مباشرة\n"
                        "ℹ️ لمعرفة معلومات الفيديو: /info [الرابط]\n"
                        "👤 لمعلومات الحساب والموقع: /account [الرابط]\n"
                        "🔧 لحل المشاكل: /troubleshoot\n"
                        "📱 حالة المنصات: /platforms\n"
                        "📊 إحصائيات البوت: /stats (للأدمن فقط)\n\n"
                        "مثال:\n"
                        "/info https://youtube.com/watch?v=abc123\n\n"
                        "المنصات المدعومة: YouTube, Instagram, TikTok, Twitter, Facebook وأكثر من 1000 منصة أخرى!"
                    )
                    self.send_message(chat_id, help_message)
                elif message['text'] == '/troubleshoot':
                    troubleshoot_message = (
                        "🔧 حل مشاكل التحميل:\n\n"
                        "❌ إذا فشل التحميل، جرب:\n\n"
                        "📱 انستقرام:\n"
                        "• الروابط العامة تعمل أفضل\n"
                        "• المحتوى الخاص يحتاج تسجيل دخول\n"
                        "• حاول مرة أخرى بعد دقائق\n\n"
                        "📺 يوتيوب:\n"
                        "• تأكد من أن الفيديو عام\n"
                        "• الفيديوهات المقيدة بالعمر قد تفشل\n\n"
                        "🔄 حلول عامة:\n"
                        "• تأكد من صحة الرابط\n"
                        "• جرب رابط آخر من نفس المنصة\n"
                        "• أعد إرسال الرابط بعد دقائق\n\n"
                        "💡 نصيحة: استخدم /info [الرابط] لفحص الفيديو قبل التحميل"
                    )
                    self.send_message(chat_id, troubleshoot_message)
                elif message['text'] == '/platforms':
                    platforms_message = (
                        "📱 حالة المنصات المدعومة:\n\n"
                        "✅ تعمل بشكل ممتاز:\n"
                        "• YouTube - جميع الفيديوهات العامة\n"
                        "• TikTok - معظم الفيديوهات\n"
                        "• Twitter - الفيديوهات العامة\n"
                        "• Facebook - الفيديوهات العامة\n\n"
                        "⚠️ تعمل أحياناً:\n"
                        "• Instagram - الفيديوهات العامة فقط\n"
                        "• Instagram Stories - قد تحتاج إعادة محاولة\n\n"
                        "❌ قيود عامة:\n"
                        "• المحتوى الخاص يحتاج تسجيل دخول\n"
                        "• الفيديوهات المقيدة بالعمر\n"
                        "• الفيديوهات المحذوفة أو المحظورة\n\n"
                        "💡 نصيحة: ابدأ بـ YouTube و TikTok للحصول على أفضل النتائج"
                    )
                    self.send_message(chat_id, platforms_message)
                elif message['text'].startswith('/info '):
                    url = message['text'][6:].strip()  # Remove '/info ' prefix
                    if url.startswith(('http://', 'https://')):
                        self.handle_info_command(chat_id, url)
                    else:
                        self.send_message(chat_id, "❌ يرجى إرسال رابط صحيح بعد الأمر /info")
                elif message['text'].startswith('/account '):
                    url = message['text'][9:].strip()  # Remove '/account ' prefix
                    if url.startswith(('http://', 'https://')):
                        self.handle_account_command(chat_id, url)
                    else:
                        self.send_message(chat_id, "❌ يرجى إرسال رابط صحيح بعد الأمر /account")
                elif message['text'] == '/stats' and chat_id == self.config.ADMIN_ID:
                    stats_message = (
                        f"📊 إحصائيات البوت:\n\n"
                        f"👥 إجمالي المستخدمين: {self.download_stats['total_users']}\n"
                        f"📥 إجمالي التحميلات: {self.download_stats['total_downloads']}\n"
                        f"✅ تحميلات ناجحة: {self.download_stats['successful_downloads']}\n"
                        f"❌ تحميلات فاشلة: {self.download_stats['failed_downloads']}\n"
                        f"📈 معدل النجاح: {(self.download_stats['successful_downloads'] / max(1, self.download_stats['total_downloads']) * 100):.1f}%"
                    )
                    self.send_message(chat_id, stats_message)
                return
            
            # Handle URL messages
            if 'text' in message:
                text = message['text'].strip()
                if text.startswith(('http://', 'https://')):
                    self.handle_url_message(chat_id, text)
                else:
                    self.send_message(
                        chat_id,
                        "❌ يرجى إرسال رابط صحيح\n"
                        "مثال: https://youtube.com/watch?v=...\n\n"
                        "💡 نصيحة: استخدم /platforms لمعرفة أفضل المنصات للتحميل"
                    )
        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def run(self):
        """Main bot loop"""
        logger.info("🚀 Starting Telegram bot...")
        
        while True:
            try:
                updates = self.get_updates()
                
                for update in updates:
                    if 'message' in update:
                        self.handle_message(update['message'])
                
                time.sleep(self.config.POLLING_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)  # Wait before retrying
