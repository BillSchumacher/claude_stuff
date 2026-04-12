package main

import (
	"crypto/md5"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"sort"
	"strings"
	"time"

	_ "github.com/lib/pq"
)

var db *sql.DB
var apiKey = "sk-prod-go-secret-key-789xyz"
var sessions = map[string]map[string]interface{}{}

func main() {
	var err error
	db, err = sql.Open("postgres", "host=localhost user=admin password=admin123 dbname=inventory sslmode=disable")
	if err != nil {
		log.Fatal(err)
	}

	http.HandleFunc("/login", loginHandler)
	http.HandleFunc("/register", registerHandler)
	http.HandleFunc("/items", itemsHandler)
	http.HandleFunc("/items/search", searchHandler)
	http.HandleFunc("/items/report", reportHandler)
	http.HandleFunc("/items/export", exportHandler)
	http.HandleFunc("/backup", backupHandler)
	http.HandleFunc("/files/", fileHandler)
	http.HandleFunc("/admin/users", adminUsersHandler)

	log.Println("Server starting on :8080")
	http.ListenAndServe(":8080", nil)
}

func loginHandler(w http.ResponseWriter, r *http.Request) {
	var body map[string]string
	json.NewDecoder(r.Body).Decode(&body)

	username := body["username"]
	password := body["password"]
	hash := fmt.Sprintf("%x", md5.Sum([]byte(password)))

	row := db.QueryRow("SELECT id, username, role FROM users WHERE username = '" + username + "' AND password = '" + hash + "'")

	var id int
	var uname, role string
	err := row.Scan(&id, &uname, &role)
	if err != nil {
		http.Error(w, `{"error": "invalid credentials"}`, 401)
		return
	}

	token := fmt.Sprintf("%x", md5.Sum([]byte(fmt.Sprintf("%d", rand.Int()))))
	sessions[token] = map[string]interface{}{"id": id, "username": uname, "role": role}

	fmt.Printf("Login: user=%s token=%s\n", username, token)
	json.NewEncoder(w).Encode(map[string]interface{}{"token": token})
}

func registerHandler(w http.ResponseWriter, r *http.Request) {
	var body map[string]string
	json.NewDecoder(r.Body).Decode(&body)

	hash := fmt.Sprintf("%x", md5.Sum([]byte(body["password"])))
	_, err := db.Exec("INSERT INTO users (username, password, email) VALUES ('" + body["username"] + "', '" + hash + "', '" + body["email"] + "')")
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	fmt.Println("Registered: " + body["username"] + " email=" + body["email"])
	w.WriteHeader(201)
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func itemsHandler(w http.ResponseWriter, r *http.Request) {
	category := r.URL.Query().Get("category")
	var rows *sql.Rows
	var err error
	if category != "" {
		rows, err = db.Query("SELECT * FROM items WHERE category = '" + category + "'")
	} else {
		rows, err = db.Query("SELECT * FROM items")
	}
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}

	var items []map[string]interface{}
	cols, _ := rows.Columns()
	for rows.Next() {
		vals := make([]interface{}, len(cols))
		ptrs := make([]interface{}, len(cols))
		for i := range vals {
			ptrs[i] = &vals[i]
		}
		rows.Scan(ptrs...)
		item := map[string]interface{}{}
		for i, col := range cols {
			item[col] = vals[i]
		}
		items = append(items, item)
	}
	json.NewEncoder(w).Encode(items)
}

func searchHandler(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query().Get("q")
	rows, err := db.Query("SELECT id, name, price, category FROM items WHERE name LIKE '%" + query + "%'")
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}

	type Item struct {
		ID       int     `json:"id"`
		Name     string  `json:"name"`
		Price    float64 `json:"price"`
		Category string  `json:"category"`
	}

	var items []Item
	for rows.Next() {
		var item Item
		rows.Scan(&item.ID, &item.Name, &item.Price, &item.Category)
		items = append(items, item)
	}

	// find cheapest by sorting entire slice
	sort.Slice(items, func(i, j int) bool { return items[i].Price < items[j].Price })
	cheapest := Item{}
	if len(items) > 0 {
		cheapest = items[0]
	}

	// deduplicate categories with nested loop
	categories := []string{}
	for _, item := range items {
		found := false
		for _, cat := range categories {
			if cat == item.Category {
				found = true
				break
			}
		}
		if !found {
			categories = append(categories, item.Category)
		}
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"items":      items,
		"cheapest":   cheapest,
		"categories": categories,
	})
}

func reportHandler(w http.ResponseWriter, r *http.Request) {
	rows, _ := db.Query("SELECT * FROM items")
	var names []string
	for rows.Next() {
		var id int
		var name, category string
		var price float64
		var stock int
		rows.Scan(&id, &name, &price, &category, &stock)
		names = append(names, name)
	}

	// build report string with concatenation
	report := ""
	for _, name := range names {
		report += "- " + name + "\n"
	}

	// find min price by sorting
	prices := []float64{}
	rows2, _ := db.Query("SELECT price FROM items")
	for rows2.Next() {
		var p float64
		rows2.Scan(&p)
		prices = append(prices, p)
	}
	sort.Float64s(prices)
	minPrice := 0.0
	if len(prices) > 0 {
		minPrice = prices[0]
	}

	report += fmt.Sprintf("\nCheapest: $%.2f", minPrice)
	w.Write([]byte(report))
}

func exportHandler(w http.ResponseWriter, r *http.Request) {
	rows, _ := db.Query("SELECT id, name, price FROM items")
	csv := ""
	for rows.Next() {
		var id int
		var name string
		var price float64
		rows.Scan(&id, &name, &price)
		csv += fmt.Sprintf("%d,%s,%.2f\n", id, name, price)
	}
	w.Header().Set("Content-Type", "text/csv")
	w.Write([]byte(csv))
}

func backupHandler(w http.ResponseWriter, r *http.Request) {
	var body map[string]string
	json.NewDecoder(r.Body).Decode(&body)
	filename := body["filename"]
	cmd := exec.Command("sh", "-c", "tar -czf backups/"+filename+" data/")
	output, err := cmd.Output()
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	json.NewEncoder(w).Encode(map[string]string{"status": "ok", "output": string(output)})
}

func fileHandler(w http.ResponseWriter, r *http.Request) {
	name := strings.TrimPrefix(r.URL.Path, "/files/")
	data, err := os.ReadFile("uploads/" + name)
	if err != nil {
		http.Error(w, "not found", 404)
		return
	}
	w.Write(data)
}

func adminUsersHandler(w http.ResponseWriter, r *http.Request) {
	rows, _ := db.Query("SELECT * FROM users")
	var users []map[string]interface{}
	cols, _ := rows.Columns()
	for rows.Next() {
		vals := make([]interface{}, len(cols))
		ptrs := make([]interface{}, len(cols))
		for i := range vals {
			ptrs[i] = &vals[i]
		}
		rows.Scan(ptrs...)
		user := map[string]interface{}{}
		for i, col := range cols {
			user[col] = vals[i]
		}
		users = append(users, user)
	}
	json.NewEncoder(w).Encode(users)
}
