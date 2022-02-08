const { Telegraf } = require("telegraf");
const cron = require("node-cron");
require("dotenv").config();

const bot = new Telegraf(process.env.BOT_TOKEN);
let reply_message = 713;
let chat_id;
let new_members = {};
let new_members_final = {};
let alert_message;
let alert_message_info;

bot.catch((err, ctx) => {
  console.log(`Ooops, encountered an error for ${ctx.updateType}`, err);
});
bot.start((ctx) => {
  console.log(ctx.message);
  ctx.reply(
    "Hi there. This bot has limited functionality. But every day it grow with new features. Come back later or contact creator @Demon_Skorosti for feature request."
  );
});
bot.on("new_chat_participant", (ctx) => {
  let user_id = ctx.message.new_chat_participant.id;
  let first_name = ctx.message.new_chat_participant.first_name;
  chat_id = ctx.message.chat.id;
  new_members[user_id] = first_name;
  console.log(new_members);
  setTimeout(() => {
    ctx.reply(
      `Приветствую ${`[${first_name}](tg://user?id=${user_id})`} , представьтесь пожалуйста по форме ^`,
      { reply_to_message_id: reply_message, parse_mode: "Markdown" }
    );
  }, 2000);
});
bot.on("message", (ctx) => {
  if (ctx.message.from.id in new_members) {
    console.log(`Removed ${new_members[ctx.message.from.id]}`);
    delete new_members[ctx.message.from.id];
  } else if (ctx.message.from.id in new_members_final) {
    console.log(`Removed ${new_members_final[ctx.message.from.id]}`);
    delete new_members_final[ctx.message.from.id];
  } else {
    if (ctx.message.left_chat_member) {
      ctx.deleteMessage(ctx.message.message_id);
    }
  }
});
cron.schedule("0 18 * * *", () => {
  new_members_final = new_members;
  new_members = {};
  if (
    Object.keys(new_members_final).length !== 0 &&
    new_members_final.constructor === Object
  ) {
    alert_message = "";
    for (let user in new_members_final) {
      alert_message = alert_message.concat(
        `${`[${new_members_final[user]}](tg://user?id=${user})`}, `
      );
    }
    bot.telegram
      .sendMessage(
        chat_id,
        alert_message.concat(
          "последнее предупреждение перед удалением. Представьтесь пожалуйста по форме!"
        ),
        { parse_mode: "Markdown", reply_to_message_id: reply_message }
      )
      .then((result) => {
        alert_message_info = result;
      });
  } else {
    console.log("All answered");
  }
});
cron.schedule("0 19 * * *", () => {
  for (let user in new_members_final) {
    bot.telegram.banChatMember(chat_id, user);
    bot.telegram.unbanChatMember(chat_id, user);
    console.log(`${user} Kicked`);
    bot.telegram.deleteMessage(
      alert_message_info.chat.id,
      alert_message_info.message_id
    );
    console.log("Message deleted");
  }
});
bot.launch();

process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));
