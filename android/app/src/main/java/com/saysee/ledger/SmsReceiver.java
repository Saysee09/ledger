package com.saysee.ledger;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.provider.Telephony;
import android.telephony.SmsMessage;

/** Gets each incoming SMS. Only money messages from bank senders are kept; everything else is dropped right here. */
public class SmsReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (!Telephony.Sms.Intents.SMS_RECEIVED_ACTION.equals(intent.getAction())) return;
        SmsMessage[] parts = Telephony.Sms.Intents.getMessagesFromIntent(intent);
        if (parts == null || parts.length == 0) return;
        StringBuilder body = new StringBuilder();
        String sender = null;
        for (SmsMessage m : parts) {
            if (m == null) continue;
            if (sender == null) sender = m.getDisplayOriginatingAddress();
            body.append(m.getDisplayMessageBody());
        }
        String text = body.toString();
        boolean money = SmsStore.looksFinancial(sender, text);
        SmsStore.noteLast(context, sender, money);
        if (!money) return;
        SmsStore.add(context, text, SmsStore.now());
        Widgets.bumpSort(context);
        if (!MainActivity.ping()) SmsStore.notify(context, text);
    }
}
