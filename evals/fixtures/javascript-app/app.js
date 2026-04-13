const express = require("express");
const mysql = require("mysql");
const crypto = require("crypto");
const { exec } = require("child_process");
const fs = require("fs");

const app = express();
app.use(express.json());

const API_SECRET = "sk-live-prod-secret-key-abc123";
const JWT_SECRET = "jwt-super-secret";

const db = mysql.createConnection({
  host: "localhost",
  user: "root",
  password: "root123",
  database: "shop",
});

// Global state
var sessions = {};
var cache = {};

app.post("/login", function (req, res) {
  var username = req.body.username;
  var password = req.body.password;
  var hash = crypto.createHash("md5").update(password).digest("hex");
  db.query(
    "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + hash + "'",
    function (err, results) {
      if (err) {
        res.status(500).json({ error: err.message, stack: err.stack });
        return;
      }
      if (results.length > 0) {
        var token = crypto.createHash("md5").update(Math.random().toString()).digest("hex");
        sessions[token] = results[0];
        console.log("Login: " + username + " token=" + token);
        res.json({ token: token, user: results[0] });
      } else {
        res.status(401).json({ error: "wrong password" });
      }
    }
  );
});

app.post("/register", function (req, res) {
  var hash = crypto.createHash("sha256").update(req.body.password).digest("hex");
  db.query(
    `INSERT INTO users (username, password, email) VALUES ('${req.body.username}', '${hash}', '${req.body.email}')`,
    function (err) {
      if (err) {
        res.status(500).json({ error: err.message });
        return;
      }
      res.json({ status: "ok" });
    }
  );
});

app.get("/products", function (req, res) {
  var category = req.query.category || "";
  var sort = req.query.sort || "name";
  db.query(
    "SELECT * FROM products WHERE category = '" + category + "' ORDER BY " + sort,
    function (err, results) {
      if (err) {
        res.status(500).json({ error: err.toString() });
        return;
      }
      res.json(results);
    }
  );
});

app.post("/products", function (req, res) {
  var data = req.body;
  db.query(
    `INSERT INTO products (name, price, category, stock) VALUES ('${data.name}', ${data.price}, '${data.category}', ${data.stock})`,
    function (err, result) {
      if (err) {
        res.status(500).json({ error: err.message });
        return;
      }
      res.json({ id: result.insertId });
    }
  );
});

app.get("/products/search", function (req, res) {
  var q = req.query.q;
  db.query("SELECT * FROM products", function (err, products) {
    if (err) {
      res.status(500).json({ error: err.message });
      return;
    }
    // filter in JS instead of SQL
    var filtered = products.filter(function (p) {
      return p.name.toLowerCase().includes(q.toLowerCase());
    });
    // deduplicate by name using nested loop
    var unique = [];
    for (var i = 0; i < filtered.length; i++) {
      var found = false;
      for (var j = 0; j < unique.length; j++) {
        if (unique[j].name === filtered[i].name) {
          found = true;
          break;
        }
      }
      if (!found) unique.push(filtered[i]);
    }
    res.json(unique);
  });
});

app.get("/products/export", function (req, res) {
  db.query("SELECT * FROM products", function (err, products) {
    if (err) {
      res.status(500).json({ error: err.message });
      return;
    }
    var csv = "";
    for (var i = 0; i < products.length; i++) {
      csv += products[i].id + "," + products[i].name + "," + products[i].price + "\n";
    }
    res.send(csv);
  });
});

app.get("/orders/:userId", function (req, res) {
  db.query(
    "SELECT * FROM orders WHERE user_id = " + req.params.userId,
    function (err, results) {
      if (err) {
        res.status(500).json({ error: err.message });
        return;
      }
      res.json(results);
    }
  );
});

app.post("/orders/:userId/process", function (req, res) {
  var queue = req.body.items.slice();
  var processed = [];
  while (queue.length > 0) {
    var item = queue.shift();
    processed.push({ item: item, status: "processed" });
  }
  res.json({ processed: processed });
});

app.get("/report/sales", function (req, res) {
  db.query("SELECT * FROM orders", function (err, orders) {
    if (err) {
      res.status(500).json({ error: err.message });
      return;
    }
    // find top products by counting in nested loop
    var products = [];
    for (var i = 0; i < orders.length; i++) {
      if (!products.includes(orders[i].product_id)) {
        products.push(orders[i].product_id);
      }
    }
    var counts = [];
    for (var i = 0; i < products.length; i++) {
      var count = 0;
      for (var j = 0; j < orders.length; j++) {
        if (orders[j].product_id === products[i]) count++;
      }
      counts.push({ product_id: products[i], count: count });
    }
    counts.sort(function (a, b) { return b.count - a.count; });
    res.json(counts);
  });
});

app.post("/backup", function (req, res) {
  var filename = req.body.filename;
  exec("tar -czf backups/" + filename + " data/", function (err, stdout) {
    if (err) {
      res.status(500).json({ error: err.message });
      return;
    }
    res.json({ status: "backup created" });
  });
});

app.get("/files/:name", function (req, res) {
  var filepath = "uploads/" + req.params.name;
  res.sendFile(filepath);
});

app.get("/admin/users", function (req, res) {
  db.query("SELECT * FROM users", function (err, results) {
    res.json(results);
  });
});

if (process.env.START_SERVER) {
  app.listen(3000, function () {
    console.log("Server running on port 3000");
  });
}
