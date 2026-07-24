import os
import sys
import logging
import random
import asyncio
import threading
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bot")

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ShopMainView())
        self.add_view(DepositButtonView())
        self.add_view(FortuneView())
        await self.tree.sync()
        log.info("Synced slash commands!")

    async def on_ready(self):
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        log.info("Connected to %d guild(s)", len(self.guilds))


bot = MyBot()


# --- ShuffleVoiceView ---
class ShuffleVoiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)

    async def check_user_in_voice(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ เธอต้องเข้าห้องเสียง (Voice Channel) ไหนสักห้องก่อนนะคะ ถึงจะกดปุ่มนี้ได้!",
                ephemeral=True,
            )
            return None
        return interaction.user.voice.channel

    @discord.ui.button(label="มีคน", style=discord.ButtonStyle.secondary, emoji="🤍")
    async def join_occupied(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_channel = await self.check_user_in_voice(interaction)
        if not current_channel:
            return
        channels = [
            ch for ch in interaction.guild.voice_channels
            if len(ch.members) > 0 and ch.id != current_channel.id
        ]
        if not channels:
            await interaction.response.send_message(
                "ตอนนี้ไม่มีห้องอื่นที่มีคนอยู่เลยค่ะ 🥺", ephemeral=True
            )
            return
        target_channel = random.choice(channels)
        await interaction.user.move_to(target_channel)
        await interaction.response.send_message(
            f"✨ ย้ายเธอไปห้อง **{target_channel.name}** เรียบร้อยแล้วค่ะ! ขอให้สนุกน้า",
            ephemeral=True, delete_after=60,
        )

    @discord.ui.button(label="ไม่มีคน", style=discord.ButtonStyle.danger, emoji="🩷")
    async def join_empty(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_channel = await self.check_user_in_voice(interaction)
        if not current_channel:
            return
        channels = [ch for ch in interaction.guild.voice_channels if len(ch.members) == 0]
        if not channels:
            await interaction.response.send_message(
                "ตอนนี้ห้องเสียงเต็มหมดแล้ว ไม่มีห้องว่างเลยค่ะ 😭", ephemeral=True
            )
            return
        target_channel = random.choice(channels)
        await interaction.user.move_to(target_channel)
        await interaction.response.send_message(
            f"✨ ย้ายเธอไปห้องส่วนตัวที่ว่างอยู่ **{target_channel.name}** เรียบร้อยแล้วค่ะ!",
            ephemeral=True, delete_after=60,
        )

    @discord.ui.button(label="ออกห้อง", style=discord.ButtonStyle.primary, emoji="💛")
    async def leave_voice(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_channel = await self.check_user_in_voice(interaction)
        if not current_channel:
            return
        await interaction.user.move_to(None)
        await interaction.response.send_message(
            "👋 ออกจากห้องเสียงให้เรียบร้อยแล้วค่ะ ไว้มาเล่นใหม่น้า!", ephemeral=True, delete_after=60
        )


# --- /sooi ---
@bot.tree.command(name="sooi", description="เรียกบอทสุ่มห้องเสียงน่ารักๆ")
async def sooi_command(interaction: discord.Interaction):
    msg_text = (
        "## สวัสดีค่ะ\n"
        "หนูเป็นบอทน้า^^\n"
        "ต้องการสุ่มห้องใช่มั้ย\n"
        "1. กดเข้าห้องด้านล่างนี่เลย\n"
        "2. และกดปุ่มด้านล่างนี้ค่ะ\n"
        "2.1🤍: ย้ายไปห้องมีที่คน\n"
        "2.2🩷: ย้ายไปห้องที่ไม่มีคน\n"
        "2.3💛: ออกห้อง\n"
        "3. รอย้ายห้องค่ะ\n"
        "คุยให้สนุกน้าา"
    )
    embed = discord.Embed(description=msg_text, color=0xFFFFFF)
    view = ShuffleVoiceView()
    banner_path = os.path.join(os.path.dirname(__file__), "banner.jpg")
    try:
        file = discord.File(banner_path, filename="banner.jpg")
        embed.set_image(url="attachment://banner.jpg")
        await interaction.response.send_message(embed=embed, file=file, view=view)
    except FileNotFoundError:
        await interaction.response.send_message(embed=embed, view=view)


async def auto_delete(interaction: discord.Interaction, delay: int):
    await asyncio.sleep(delay)
    try:
        await interaction.delete_original_response()
    except Exception:
        pass


# --- /eoii ---
class PaymentModal(discord.ui.Modal, title="💰 จ่ายเงินตามใจชอบ"):
    amount_input = discord.ui.TextInput(
        label="ใส่จำนวนเงินตามใจเธอเลยค่ะ",
        placeholder="เช่น 999999 / ตามใจเธอเลย...",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"ทานให้อร่อยน้าา ได้รับเงินจำนวน **{self.amount_input.value}** แล้วค่ะ :3",
        )
        asyncio.create_task(auto_delete(interaction, 120))


class PayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="จ่ายเงิน", style=discord.ButtonStyle.success, emoji="💵")
    async def pay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PaymentModal())


class ShopMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def process_order(self, interaction: discord.Interaction, item_type: str):
        msg_text = (
            f"## เลือกซื้อ{item_type}หรอ\n"
            "ได้เลยค่ะ^^\n"
            "ใส่ถุงให้แล้วน้าา\n"
            "จ่ายเงินเลยค่ะ(ตามใจ^^)"
        )
        await interaction.response.send_message(content=msg_text, view=PayView())
        asyncio.create_task(auto_delete(interaction, 120))

    @discord.ui.button(label="น้ำ", style=discord.ButtonStyle.primary, emoji="💧", custom_id="shop:water")
    async def button_water(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_order(interaction, "น้ำ")

    @discord.ui.button(label="ขนม", style=discord.ButtonStyle.primary, emoji="🍪", custom_id="shop:snack")
    async def button_snack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_order(interaction, "ขนม")

    @discord.ui.button(label="ของหวาน", style=discord.ButtonStyle.primary, emoji="🍰", custom_id="shop:sweet")
    async def button_sweet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_order(interaction, "ของหวาน")

    @discord.ui.button(label="อื่นๆ", style=discord.ButtonStyle.secondary, emoji="🎁", custom_id="shop:other")
    async def button_other(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_order(interaction, "อื่นๆ")


@bot.tree.command(name="eoii", description="เปิดร้านค้าจำลองสุดน่ารัก")
async def eoii_command(interaction: discord.Interaction):
    welcome_text = (
        "## ยินดีต้อนรับค้าา\n"
        "รับอะไรดีค้าา\n"
        "น้ำ ขนม ของหวาน หรืออื่นๆ\n"
        "ที่นี่มีให้ท่านหมดแล้วล่ะ\n"
        "เลือกเลย↓↓"
    )
    embed = discord.Embed(description=welcome_text, color=0x89CFF0)
    shop_banner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop_banner.jpg")
    try:
        file = discord.File(shop_banner_path, filename="shop_banner.jpg")
        embed.set_image(url="attachment://shop_banner.jpg")
        await interaction.response.send_message(embed=embed, file=file, view=ShopMainView())
    except FileNotFoundError:
        await interaction.response.send_message(embed=embed, view=ShopMainView())


# --- /aooi ---
class DepositModal(discord.ui.Modal, title="📝 ฟอร์มฝากข้อความ"):
    message_input = discord.ui.TextInput(
        label="ช่องที่ 1 ฝากข้อความ",
        style=discord.TextStyle.paragraph,
        placeholder="พิมพ์ข้อความที่ต้องการฝากตรงนี้เลยค่ะ...",
        required=True,
        max_length=1000,
    )
    hint_input = discord.ui.TextInput(
        label="ช่อง 2 ใบ้",
        style=discord.TextStyle.short,
        placeholder="ใบ้ตัวตนของเธอหน่อยเร็ว...",
        required=True,
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        TARGET_CHANNEL_ID = 1526235721332162681
        channel = interaction.guild.get_channel(TARGET_CHANNEL_ID)
        if channel is None:
            await interaction.response.send_message(
                "❌ ไม่พบห้องสำหรับส่งข้อความฝาก (โปรดเช็ก ID ห้องอีกครั้ง)", ephemeral=True
            )
            return
        embed_content = (
            "สวัสดีค่า มีข้อความมา𓂃\n"
            "ข้อความฝากบอกคนน่ารัก\n"
            f"🐽: {self.message_input.value}\n\n"
            "ใบ้ (ถึงคนส่ง)💞\n"
            f"🐽: {self.hint_input.value}\n\n"
            "อยากตอบกลับมั้ยย^^"
        )
        try:
            embed = discord.Embed(description=embed_content, color=0xFFB6C1)
            banner2_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banner2.jpg")
            try:
                file = discord.File(banner2_path, filename="banner2.jpg")
                embed.set_image(url="attachment://banner2.jpg")
                await channel.send(embed=embed, file=file)
            except FileNotFoundError:
                await channel.send(embed=embed)
            await interaction.response.send_message(
                "✨ ส่งข้อความฝากเรียบร้อยแล้วค่ะ! รอคนน่ารักมาอ่านน้า", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"เกิดข้อผิดพลาดในการส่งข้อความ: {e}", ephemeral=True
            )


class DepositButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ฝากข้อความ", style=discord.ButtonStyle.primary, emoji="📝", custom_id="deposit:open")
    async def deposit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DepositModal())


@bot.tree.command(name="aooi", description="ส่งระบบฝากข้อความสุดน่ารัก")
async def aooi_command(interaction: discord.Interaction):
    welcome_text = (
        "อยากฝากข้อความมั้ยคะ \n"
        "1. กดปุ่มนี่เลย\n"
        "2. ใส่ข้อความ\n"
        "3. ใบ้(ตัวเรา)\n"
        "4. รอเลยย\n"
        "ส่งให้คนน่ารักเลยค่ะ🩷"
    )
    embed = discord.Embed(description=welcome_text, color=0xFFB6C1)
    view = DepositButtonView()
    await interaction.response.send_message(embed=embed, view=view)


# --- /qoll ---
fortunes = {
    "love": [
        "❤️ ช่วงนี้มีคนแอบมองเธออยู่นะ แต่เขาอาจจะยังไม่กล้าทัก หรือถ้าเธอมีคู่แล้ว ช่วงนี้อาจจะมีงอนกันเรื่องเล็กๆ น้อยๆ แต่สุดท้ายก็รักกันดีค่ะ!",
        "❤️ คนโสดช่วงนี้เสน่ห์แรงเป็นพิเศษ จะมีคนเข้ามาทำให้ใจฟู แต่อย่าเพิ่งรีบร้อนดูกันไปยาวๆ ส่วนคนมีคู่ แฟนเธอช่วงนี้อาจจะดื้อหน่อยนะ ต้องดุเบาๆ ค้าบ",
        "❤️ ดวงความรักช่วงนี้เน้นความสบายใจค่ะ อยู่กับใครแล้วเป็นตัวของตัวเอง คนนั้นแหละคือคนที่ใช่ ส่วนใครที่รอคนเก่าๆ เดินหน้าต่อดีกว่า มีสิ่งดีๆ รออยู่ข้างหน้าค่ะ!",
        "❤️ ช่วงนี้เธอดูน่ารักเป็นพิเศษนะ! คนรอบข้างอยากเข้าหา แต่เธอเองอาจจะยังรู้สึกรักสันโดษอยู่ขำๆ หรือถ้ามีแฟน แฟนจะสปอยล์เธอมากๆ ในช่วงนี้เลยล่ะ",
        "❤️ คนโสดระวังโดนตกเพราะแพ้ทางคนใส่ใจเล็กๆ น้อยๆ ส่วนคนมีคู่ให้ระวังเรื่องการประชดประชันกันนะ พูดกันตรงๆ น่ารักกว่าเยอะเลยค่ะ",
        "❤️ มีเกณฑ์จะได้คุยกับคนที่มีบุคลิกต่างจากเธอมากๆ แต่กลับเข้ากันได้ดีอย่างน่าประหลาด! เปิดใจไว้หน่อยน้า อาจจะมีเซอร์ไพรส์",
        "❤️ ช่วงนี้สายเปย์มาก! ถ้ามีแฟน เธอจะอยากซื้อนู่นซื้อนี่ให้แฟน หรือถ้ายังโสด ก็เปย์ตัวเองจนใจฟูไปเลยค่ะ ความรักตัวเองก็คือความรักที่ดีที่สุดนะ",
        "❤️ ระวังความคิดมากของตัวเองนะเธอ บางทีเขาไม่ได้คิดอะไรเลย แต่เราคิดไปไกลแล้ว 5555 ถอยออกมามองกว้างๆ แล้วจะเห็นว่าเขายังใส่ใจเธอเหมือนเดิมค่ะ",
        "❤️ ดวงความรักเรียบๆ แต่มีความสุขดีค่ะ ไม่มีดราม่าใหญ่โต เหมาะกับการชวนกันไปหาของอร่อยกิน หรือนั่งคุยกันเงียบๆ ซึมซับบรรยากาศสบายๆ",
        "❤️ คนโสดมีเกณฑ์เจอคนคุยผ่านทางออนไลน์/เกม/ Discord นี่แหละ! ลองสังเกตคนที่เข้ามาทักช่วงนี้ดูนะ อาจจะมีคนแอบเนียนมาจีบอยู่ค่ะ",
    ],
    "work": [
        "💼 ช่วงนี้เธอรู้สึกเหนื่อยๆ หรือเบื่อๆ กับสิ่งที่ทำอยู่ใช่ไหม? มีเรื่องให้คิดในหัวเยอะมาก แต่เชื่อเถอะว่าความพยายามของเธอจะไม่สูญเปล่า คนรอบข้างแอบมองความเก่งของเธออยู่ค่ะ",
        "💼 ดวงการงาน/การเรียนปังมาก! มีเกณฑ์จะได้รับโอกาสใหม่ๆ หรือทำงานสำเร็จตามที่ตั้งใจไว้ แต่อาจจะต้องระวังเรื่องการนอนดึกหรือพักผ่อนไม่เพียงพอนะคะ",
        "💼 ช่วงนี้งานหรือการเรียนอาจจะถาโถมเข้ามาพร้อมกันจนทำตัวไม่ถูก แต่เธอจะผ่านมันไปได้ด้วยไหวพริบของตัวเองค่ะ จะมีคนยื่นมือเข้ามาช่วยในจังหวะสุดท้ายพอดี!",
        "💼 มีเกณฑ์ได้รับคำชมหรือผลลัพธ์ที่ดีจากสิ่งที่ลงมือทำไปก่อนหน้านี้ ใครที่กำลังรอฟังข่าวดีเรื่องงานหรือการสอบ มีลุ้นมากๆ เลยล่ะค่ะ สู้ๆ นะคะ",
        "💼 สมองช่วงนี้แล่นไวมาก! คิดไอเดียอะไรใหม่ๆ ออกได้ง่าย เหมาะกับการเริ่มโปรเจกต์ใหม่ๆ หรือลุยงานที่ค้างไว้ให้เสร็จ ลุยเลยเธอ!",
        "💼 ระวังเรื่องการลืมของหรือลืมส่งงานนิดนึงนะช่วงนี้ สมาธิอาจจะหลุดง่ายไปหน่อย แนะนำให้จด To-do list ไว้กันพลาดค่ะ",
        "💼 ช่วงนี้รู้สึกเหมือนแบกโลกไว้ทั้งใบใช่ไหม? หาเวลาพักผ่อนบ้างนะ อย่าตึงกับตัวเองเกินไป ทำทีละอย่างแล้วมันจะค่อยๆ คลี่คลายเองค่ะ",
        "💼 มีเกณฑ์ได้ทำงานร่วมกับคนที่เก่งๆ แล้วจะได้รับพลังบวกหรือได้ความรู้ใหม่ๆ กลับมาเยอะมาก เป็นช่วงเก็บเกี่ยวประสบการณ์ที่ดีเลยล่ะ",
        "💼 อุปสรรคเล็กๆ น้อยๆ ช่วงนี้จะกลายเป็นเรื่องหมูๆ ถ้าเธอตั้งสติ อย่าเพิ่งลนนะ เธอเก่งกว่าที่ตัวเองคิดเยอะเลย!",
        "💼 ผลงานที่เธอซุ่มทำอยู่เงียบๆ กำลังจะส่งผลให้คนอื่นเห็นและยอมรับในตัวเธอแล้ว วางใจได้เลยค่ะ ผลลัพธ์ออกมาคุ้มค่าแน่นอน",
    ],
    "finance": [
        "💰 มีเกณฑ์เสียเงินไปกับของที่ชอบหรือของตามใจตัวเอง (เช่น ของกินอร่อยๆ หรือของน่ารักๆ) แต่ดวงการเงินโดยรวมยังหมุนเงินทันอยู่ค่ะ แค่ต้องหักห้ามใจกับป้ายเซลส์นิดนึงนะ!",
        "💰 ช่วงนี้โชคลาภกำลังเดินทางมาหาเธอค่ะ! อาจจะได้เงินก้อนเล็กๆ หรือมีคนเอาของกิน ของขวัญมาเปย์ให้ถึงที่ เงินในกระเป๋ายังนิ่งๆ แต่กระเป๋าไม่ฉีกแน่นอนค้าา",
        "💰 ดวงกระเป๋าตังค์ช่วงนี้: รายรับเข้ามาเรื่อยๆ แต่รายจ่ายก็รออยู่เป็นหางว่าวเลย 5555 แนะนำให้แบ่งเงินเก็บไว้บ้างนะเผื่อฉุกเฉิน แต่รวมๆ แล้วเอาตัวรอดได้สบายค่ะ",
        "💰 ช่วงนี้การเงินดีขึ้นกว่าช่วงก่อนหน้านี้ มีเกณฑ์มีคนอุปถัมภ์ หรือแฟน/คนสนิทแอบเปย์ให้จับจ่ายใช้สอยแบบฟินๆ ทานของอร่อยๆ ได้เต็มที่เลยค่ะ!",
        "💰 ยอดเงินในบัญชีช่วงนี้เข้าออกไวเหมือนสายน้ำไหล 5555 เพิ่งเข้าเมื่อกี้ ไหลออกไปกับของกินอีกแล้ว! แต่ไม่เดือดร้อนแน่นอนค่ะ หมุนทันอยู่",
        "💰 มีดวงเรื่องลาภลอยแบบไม่ทันตั้งตัว! อาจจะเป็นเงินทอนเกิน ได้ส่วนลดพิเศษ หรือจับฉลากได้ของรางวัล ลองเสี่ยงโชคเล็กๆ น้อยๆ ดูได้นะ",
        "💰 ห้ามใจตัวเองกับของกดสั่งออนไลน์หน่อยน้าา ช่วงนี้กดลงตะกร้าเพลินมาก! ถ้ายับยั้งชั่งใจได้ เงินเก็บจะเพิ่มขึ้นเยอะเลยล่ะ",
        "💰 ช่วงนี้ดวงการเงินสายสปอยล์ตัวเองหนักมาก อยากได้อะไรก็ซื้อ แต่ก็แลกมาด้วยความสุขใจ ถือว่าซื้อความสุขให้ตัวเองน้า ไม่เป็นไร!",
        "💰 มีเกณฑ์จะได้เงินคืนจากคนที่เคยยืมไป หรือได้เงินปันผล/ผลตอบแทนจากสิ่งที่เคยลงทุนไว้ สภาพคล่องถือว่าดีเยี่ยมเลยค่ะ",
        "💰 การเงินช่วงนี้มั่นคงดีมาก ไม่มีเรื่องให้ต้องเครียดกังวลใจ แต่อาจจะหมดไปกับค่าเดินทางหรือการไปเที่ยวพักผ่อนนิดหน่อยค่ะ",
    ],
}


class FortuneView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ความรัก", style=discord.ButtonStyle.danger, emoji="🤍", custom_id="fortune:love")
    async def love_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        fortune = random.choice(fortunes["love"])
        embed = discord.Embed(description=f"🔮 **ดวงความรักของเธอ:**\n{fortune}", color=0x4B0082)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="การงาน", style=discord.ButtonStyle.primary, emoji="💼", custom_id="fortune:work")
    async def work_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        fortune = random.choice(fortunes["work"])
        embed = discord.Embed(description=f"🔮 **ดวงการงาน/การเรียนของเธอ:**\n{fortune}", color=0x4B0082)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="การเงิน", style=discord.ButtonStyle.success, emoji="💰", custom_id="fortune:finance")
    async def finance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        fortune = random.choice(fortunes["finance"])
        embed = discord.Embed(description=f"🔮 **ดวงการเงินของเธอ:**\n{fortune}", color=0x4B0082)
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="qoll", description="ดูดวงแม่นๆ สุดน่ารัก")
async def qoll_command(interaction: discord.Interaction):
    welcome_text = (
        "## ดูดวงใช่มั้ยย\n"
        "เลือกที่อยากดูเลยค่ะ\n"
        "(ดูเล่นๆน้า)อย่าจริงจังนะคะ\n"
        "มาเริ่มกันเลยย:3"
    )
    embed = discord.Embed(description=welcome_text, color=0x4B0082)
    fortune_banner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fortune_banner.webp")
    try:
        file = discord.File(fortune_banner_path, filename="fortune_banner.webp")
        embed.set_image(url="attachment://fortune_banner.webp")
        await interaction.response.send_message(embed=embed, file=file, view=FortuneView())
    except FileNotFoundError:
        await interaction.response.send_message(embed=embed, view=FortuneView())


# --- Flask keep-alive (สำหรับรัน 24 ชั่วโมง) ---
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "H-pop Bot is online! 🤖", 200

def run_flask():
    port = int(os.getenv("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)


# --- Entry point ---
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        log.critical("DISCORD_TOKEN is not set.")
        sys.exit(1)

    threading.Thread(target=run_flask, daemon=True).start()

    try:
        bot.run(token, log_handler=None)
    except discord.errors.LoginFailure:
        log.critical("Invalid DISCORD_TOKEN.")
        sys.exit(1)
