import asyncio
from telegram import Bot
import os
from src.logger import Logger
from src.mongodb_client import MongoDBClient
from src.script import load_config
from collections import defaultdict

logger = Logger("TelegramPusher")

async def send_message(bot, chat_id, message, topic_id=None):
    try:
        if topic_id:
            await bot.send_message(chat_id=chat_id, text=message, message_thread_id=topic_id)
            logger.info(f"Message sent to group {chat_id} topic {topic_id}")
        else:
            await bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Message sent to {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send to {chat_id}{' topic '+topic_id if topic_id else ''}: {e}")
        return False

def get_telegram_topics(mongodb_client: MongoDBClient, group_id=None):
    try:
        db_name = 'igs_project'
        collection_name = "telegram_topic"
        
        # 如果提供了群組ID，則進行篩選
        filter_dict = {}
        if group_id:
            filter_dict = {"group_id": group_id}
        
        topics = mongodb_client.query_by_fields(
            db_name, 
            collection_name,
            filter_dict=filter_dict
        )
        
        if not topics:
            if group_id:
                logger.warning(f"未找到群組 {group_id} 的任何Telegram主題設定")
            else:
                logger.warning("未找到任何Telegram主題設定")
            return {}
            
        topic_map = {}
        for topic in topics:
            topic_relate = topic.get("topic_relate")
            topic_id = topic.get("topic_id")
            group_id = topic.get("group_id")
            if topic_relate and topic_id and group_id:
                topic_map[topic_relate] = {"topic_id": topic_id, "group_id": group_id}
                
        logger.info(f"已載入 {len(topic_map)} 個Telegram主題設定")
        return topic_map
    except Exception as e:
        logger.error(f"獲取Telegram主題資訊時發生錯誤: {e}")
        return {}

def get_weekly_report_data_by_category(mongodb_client: MongoDBClient):
    try:
        db_name = 'igs_project'
        collection_name = "insight_report"
        
        # 先獲取所有類別
        all_categories = mongodb_client.get_distinct(db_name, collection_name, "category")
        
        if not all_categories:
            logger.error("未找到任何類別資料")
            return {}, None
            
        logger.info(f"找到 {', '.join(all_categories)} 個類別")
        
        reports_by_category = defaultdict(list)
        category_dates = {}
        
        # 針對每個類別，查詢其最新日期的資料
        for category in all_categories:
            # 獲取該類別的所有日期
            category_all_dates = mongodb_client.get_distinct(
                db_name, 
                collection_name, 
                "created_at",
                filter_dict={"category": category}
            )
            
            if not category_all_dates:
                logger.warning(f"類別 {category} 未找到任何日期資料，跳過")
                continue
                
            # 按時間排序，找出最新日期
            category_all_dates.sort(reverse=True)
            category_latest_date = category_all_dates[0]
            logger.info(f"類別 {category} 的最新日期是: {category_latest_date}")
            
            # 記錄此類別的最新日期，用於後續格式化
            category_dates[category] = category_latest_date
            
            # 獲取該類別最新日期的報告
            category_reports = mongodb_client.query_by_fields(
                db_name, 
                collection_name, 
                filter_dict={"category": category, "created_at": category_latest_date}
            )
            
            if not category_reports:
                logger.warning(f"類別 {category} 在日期 {category_latest_date} 沒有找到任何報告，跳過")
                continue
            
            # 將報告添加到該類別下
            reports_by_category[category] = category_reports
            logger.info(f"類別 {category} 在日期 {category_latest_date} 找到 {len(category_reports)} 份報告")
            
        if not reports_by_category:
            logger.warning("所有類別都未找到有效報告")
            return {}, None
        
        # 統一格式化日期為"週報"
        formatted_date = "本週"
        
        logger.info(f"已整理 {len(reports_by_category)} 個類別的週報資料")
        return reports_by_category, formatted_date
    except Exception as e:
        logger.error(f"獲取週報資料時發生錯誤: {e}")
        return {}, None

async def push_weekly_reports(mongodb_client, config):
    try:
        # 先獲取所有主題設定
        all_topics = get_telegram_topics(mongodb_client)
        if not all_topics:
            logger.warning("未找到任何Telegram主題設定，將嘗試檢查群組設定")
        else:
            logger.info(f"找到 {len(all_topics)} 個主題設定")

        reports_by_category, formatted_date = get_weekly_report_data_by_category(mongodb_client)
        if not reports_by_category:
            logger.warning("未找到任何週報資料，無法進行推送")
            return False
        
        if not formatted_date:
            logger.warning("無法獲取格式化日期，使用預設值")
            formatted_date = "本週"
            
        telegram_config = config.get('telegram_settings', {})
        token = telegram_config['token']
        bot = Bot(token=token)

        success_count = 0
        
        for category, reports in reports_by_category.items():
            # 優先查找該類別對應的主題設定
            topic_info = all_topics.get(category)
            
            if not topic_info:
                logger.warning(f"未找到 {category} 類別對應的Telegram主題，跳過推送")
                continue
            
            group_id = topic_info["group_id"]
            topic_id = topic_info["topic_id"]
            logger.info(f"找到 {category} 類別對應的主題 {topic_id} 在群組 {group_id}")
                
            # 分批處理報告
            chunks = [reports[i:i+10] for i in range(0, len(reports), 10)]
            chunk_sent_count = 0
            
            for i, chunk in enumerate(chunks):
                if i == 0:
                    message = f"### {category} 市場週報 {formatted_date}\n\n"
                else:
                    message = f"### {category} 市場週報 {formatted_date} (續 {i+1})\n\n"
                
                # 添加此分塊的報告內容
                for report in chunk:
                    link = report.get("link", "N/A")
                    title = report.get("標題", "N/A")
                    summary = report.get("摘要", "N/A")
                    
                    message += f"來源: {link}\n"
                    message += f"標題: {title}\n"
                    message += f"- {summary}\n\n"
                
                # 發送訊息
                if await send_message(bot, group_id, message, topic_id):
                    chunk_sent_count += 1
                    logger.info(f"成功推送 {category} 類別週報 第 {i+1}/{len(chunks)} 區塊到群組 {group_id} 主題 {topic_id}")
                else:
                    logger.error(f"推送 {category} 類別週報 第 {i+1}/{len(chunks)} 區塊到群組 {group_id} 主題 {topic_id} 失敗")
            
            # 記錄推送結果
            if chunk_sent_count > 0:
                success_count += 1
                logger.info(f"成功推送 {category} 類別週報到群組 {group_id} 主題 {topic_id}（共 {chunk_sent_count}/{len(chunks)} 個區塊）")
            else:
                logger.error(f"推送 {category} 類別週報到群組 {group_id} 主題 {topic_id} 完全失敗")
                
        logger.info(f"週報推送完成，共成功推送 {success_count} 個類別")
        return success_count > 0
    except Exception as e:
        logger.error(f"推送週報時發生錯誤: {e}")
        return False

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config', 'config.yaml')
    config = load_config(config_path=config_path)
    mongodb_uri = config.get('mongodb_settings', {}).get('uri', '')
    
    if not mongodb_uri:
        logger.error("MongoDB URI 未配置")
        exit(1)
    
    try:
        mongodbclient = MongoDBClient(uri=mongodb_uri)
        asyncio.run(push_weekly_reports(mongodbclient, config))
    except Exception as e:
        logger.error(f"執行週報推送時發生錯誤: {e}")
    finally:
        if 'mongodbclient' in locals():
            mongodbclient.close()