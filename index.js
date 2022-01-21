const { Telegraf } = require("telegraf");
require("dotenv").config();

const bot = new Telegraf(process.env.BOT_TOKEN);
let reply_message = 713;
bot.catch((err, ctx) => {
  console.log(`Ooops, encountered an error for ${ctx.updateType}`, err);
});
bot.start((ctx) =>
  ctx.reply(
    "Hi there. This bot has limited functionality. But every day it grow with new features. Come back later or contact creator @Demon_Skorosti for feature request."
  )
);
bot.on("new_chat_members", (ctx) =>
  ctx.reply(
    `Приветствую @${ctx.message.new_chat_member.username} , представтесь пожалуйста по форме ^`,
    { reply_to_message_id: reply_message }
  )
);
bot.launch();

process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));
