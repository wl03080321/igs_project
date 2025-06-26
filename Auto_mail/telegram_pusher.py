import asyncio
from telegram import Bot
import os
from src.logger import Logger
from src.mongodb_client import MongoDBClient
from src.script import load_config
from collections import defaultdict

logger = Logger("TelegramPusher")

async def send_message(bot, chat_id, message):
    try:
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Message sent to {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send to {chat_id}: {e}")
        return False

def get_telegram_groups(mongodb_client):
    try:
        db_name = 'igs_project'
        collection_name = "telegram_group"
        
        groups = mongodb_client.get_documents(db_name, collection_name)
        
        if not groups:
            logger.warning("未找到任何Telegram群組設定")
            return {}
            
        group_map = {}
        for group in groups:
            group_name = group.get("group_name")
            group_id = group.get("group_id")
            if group_name and group_id:
                group_map[group_name] = group_id
                
        logger.info(f"已載入 {len(group_map)} 個Telegram群組設定")
        return group_map
    except Exception as e:
        logger.error(f"獲取Telegram群組資訊時發生錯誤: {e}")
        return {}

def get_weekly_report_data_by_category(mongodb_client):
    try:
        db_name = 'igs_project'
        collection_name = "insight_report"
        
        all_dates = mongodb_client.get_distinct(db_name, collection_name, "date")
        
        if not all_dates:
            logger.error("未找到任何日期資料")
            return {}, None
            
        all_dates.sort(reverse=True)
        latest_date = all_dates[0]
        logger.info(f"最新的日期是: {latest_date}")
        
        reports = mongodb_client.query_by_fields(
            db_name, 
            collection_name, 
            filter_dict={"date": latest_date}
        )
        
        if not reports:
            logger.warning(f"日期 {latest_date} 沒有找到任何報告")
            return {}, None
        
        formatted_date = latest_date.replace("_", " 至 ")
        
        reports_by_category = defaultdict(list)
        for report in reports:
            category = report.get("category", "未分類")
            reports_by_category[category].append(report)
        
        logger.info(f"已整理 {len(reports_by_category)} 個類別的週報資料")
        return reports_by_category, formatted_date
    except Exception as e:
        logger.error(f"獲取週報資料時發生錯誤: {e}")
        return {}, None

async def push_weekly_reports(mongodb_client, config):
    try:
        group_map = get_telegram_groups(mongodb_client)
        if not group_map:
            logger.error("未找到任何有效的Telegram群組設定，無法進行推送")
            return False
        
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
            group_id = group_map.get(category)
            
            if not group_id:
                logger.warning(f"未找到 {category} 類別對應的Telegram群組，無法推送")
                continue
                
            chunks = [reports[i:i+10] for i in range(0, len(reports), 10)]
            chunk_sent_count = 0
            for i, chunk in enumerate(chunks):

                if i == 0:
                    message = f"### {category} 市場週報 {formatted_date}\n\n"
                else:
                    message = f"### {category} 市場週報 {formatted_date} (續 {i+1})\n\n"
                
                # 添加此分塊的報告
                for report in chunk:
                    link = report.get("link", "N/A")
                    title = report.get("標題", "N/A")
                    summary = report.get("摘要", "N/A")
                    
                    message += f"來源: {link}\n"
                    message += f"標題: {title}\n"
                    message += f"- {summary}\n\n"
                
                if await send_message(bot, group_id, message):
                    chunk_sent_count += 1
                    logger.info(f"成功推送 {category} 類別週報 第 {i+1}/{len(chunks)} 區塊到群組 {group_id}")
                else:
                    logger.error(f"推送 {category} 類別週報 第 {i+1}/{len(chunks)} 區塊到群組 {group_id} 失敗")
            
            if chunk_sent_count > 0:
                success_count += 1
                logger.info(f"成功推送 {category} 類別週報到群組 {group_id}（共 {chunk_sent_count}/{len(chunks)} 個區塊）")
            else:
                logger.error(f"推送 {category} 類別週報到群組 {group_id} 完全失敗")
                
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